using System;
using System.IO;
using System.Threading;
using System.Windows;
using System.Windows.Media;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using Google.Apis.Auth.OAuth2;
using Google.Apis.Services;
using Google.Apis.Sheets.v4;
using Google.Apis.Drive.v3;
using Google.Apis.Util.Store;
using Google.Apis.Requests;
using Google.Apis.Drive.v3.Data;
using System.Windows.Controls;
using System.Windows.Data;
using Google.Apis.Sheets.v4.Data;
using System.Threading.Tasks;
using MQTTnet;
using MQTTnet.Client;
using MQTTnet.Protocol;

namespace RFID_Securty_Solution
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
            allIDS.Add(new ID(
                "{RFID Tag ID}",
                Status.In,
                "{Name}",
                "{Item description}",
                "{Additional info}"));
            populateListView(spreadsheetPreviewListView, allIDS);
            shared = !String.IsNullOrWhiteSpace(Properties.Settings.Default.spreadsheetID);
            if (shared) serviceLogin();
            
            var factory = new MqttFactory();

            rfid_scanner_client = factory.CreateMqttClient();
            rfid_scanner_options = new MqttClientOptionsBuilder().WithWebSocketServer("broker.hivemq.com:8000/mqtt").Build();
        }

        List<ID> allIDS = new List<ID>();
        List<Log> allLogs = new List<Log>();
        static string[] Scopes = { SheetsService.Scope.Spreadsheets, DriveService.Scope.Drive };
        static string AppName = "RFID Security Solution";
        static string service_email = "security-head@rfid-security-221905.iam.gserviceaccount.com";
        private SheetsService sheets_service;
        private DriveService drive_service;
        private bool logged_in = false;
        private bool shared = false;
        private bool logging = false;
        private IMqttClient rfid_scanner_client;
        private IMqttClientOptions rfid_scanner_options;

        private async void signInButton_Click(object sender, RoutedEventArgs e)
        {
            userLogin();
            if (Regex.IsMatch(spreadsheetIDTextBox.Text, @"[-\w]{25,}"))
            {
                useExistingSpreadsheetLoadingPictureBox.Visibility = Visibility.Visible;
                allIDS.Clear();
                var spreadsheetID = spreadsheetIDTextBox.Text;
                shareSpreadsheet(spreadsheetID);

                var idVals = await getValuesFromSpreadsheet(spreadsheetID, "ids");
                var logVals = await getValuesFromSpreadsheet(spreadsheetID, "log");
                if (idVals != null && idVals.Count > 1)
                {
                    for (var i = 1; i < idVals.Count; i++)
                    {
                        Enum.TryParse((string)idVals[i][1], out Status stat);
                        allIDS.Add(new ID((string)idVals[i][0], stat, (string)idVals[i][2], (string)idVals[i][3], (string)idVals[i][4]));
                    }
                }
                if (logVals != null && logVals.Count > 1)
                {
                    for (var i = 1; i < logVals.Count; i++)
                    {
                        Enum.TryParse((string)logVals[i][1], out Status stat);
                        DateTime.TryParse((string)logVals[i][0], out DateTime timeStamp);
                        allLogs.Add(new Log(timeStamp, stat, (string)logVals[i][2], (string)logVals[i][3], (string)logVals[i][4], (string)logVals[i][5]));
                    }
                }
                populateListView(spreadsheetPreviewListView, allIDS);
                populateListView(viewSpreadsheetListView, allIDS);
                populateListView(logSpreadsheetListView, allLogs);
                useExistingSpreadsheetLoadingPictureBox.Visibility = Visibility.Hidden;
            }
        }

        private async void spreadsheetIDTextBox_TextChanged(object sender, TextChangedEventArgs e)
        {
            if (Regex.IsMatch(spreadsheetIDTextBox.Text, @"[-\w]{25,}") && logged_in)
            {
                useExistingSpreadsheetLoadingPictureBox.Visibility = Visibility.Visible;
                allIDS.Clear();
                var spreadsheetID = spreadsheetIDTextBox.Text;
                shareSpreadsheet(spreadsheetID);

                var idVals = await getValuesFromSpreadsheet(spreadsheetID, "ids");
                var logVals = await getValuesFromSpreadsheet(spreadsheetID, "log");
                if (idVals != null && idVals.Count > 1)
                {
                    for (var i = 1; i < idVals.Count; i++)
                    {
                        Enum.TryParse((string)idVals[i][1], out Status stat);
                        allIDS.Add(new ID((string)idVals[i][0], stat, (string)idVals[i][2], (string)idVals[i][3], (string)idVals[i][4]));
                    }
                }
                if (logVals != null && logVals.Count > 1)
                {
                    for (var i = 1; i < logVals.Count; i++)
                    {
                        Enum.TryParse((string)logVals[i][1], out Status stat);
                        DateTime.TryParse((string)logVals[i][0], out DateTime timeStamp);
                        allLogs.Add(new Log(timeStamp, stat, (string)logVals[i][2], (string)logVals[i][3], (string)logVals[i][4], (string)logVals[i][5]));
                    }
                }
                populateListView(spreadsheetPreviewListView, allIDS);
                populateListView(viewSpreadsheetListView, allIDS);
                populateListView(logSpreadsheetListView, allLogs);
                useExistingSpreadsheetLoadingPictureBox.Visibility = Visibility.Hidden;
            }
        }

        private void createNewSpreadsheetButton_Click(object sender, RoutedEventArgs e)
        {
            Sheet idSheet = new Sheet { Properties = new SheetProperties { Title = "ids" } };
            Sheet logSheet = new Sheet { Properties = new SheetProperties { Title = "log" } };
            Spreadsheet requestBody = new Spreadsheet
            {
                Properties = new SpreadsheetProperties(),
                Sheets = new List<Sheet> { idSheet, logSheet }
            };
            requestBody.Properties.Title = spreadsheetNameTextbox.Text;

            SpreadsheetsResource.CreateRequest request = sheets_service.Spreadsheets.Create(requestBody);

            var spreadSheet = request.Execute();
            appendNewRow(spreadSheet.SpreadsheetId, "ids", "EPC", "Status", "Owner", "Description", "Extra");
            appendNewRow(spreadSheet.SpreadsheetId, "log", "Time", "Status", "EPC", "Owner", "Description", "Extra");
            spreadsheetIDTextBox.Text = spreadSheet.SpreadsheetId;
        }

        private void viewSpreadsheetListView_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            var ID = (ID)e.AddedItems[0];
            activeTagTextbox.Text = ID.EPC;
            tagStatusComboBox.SelectedIndex = (int)ID.Status;
            tagOwnerTextbox.Text = ID.Owner;
            tagDescriptionTextbox.Text = ID.Description;
            tagExtraTextbox.Text = ID.Extra;
        }

        private void updateTagButton_Click(object sender, RoutedEventArgs e)
        {
            var index = viewSpreadsheetListView.SelectedIndex;
            var values = new List<object>()
            {
                activeTagTextbox.Text,
                ((Status)tagStatusComboBox.SelectedIndex).ToString(),
                tagOwnerTextbox.Text,
                tagDescriptionTextbox.Text,
                tagExtraTextbox.Text,
            };
            allIDS[index].Status = (Status)tagStatusComboBox.SelectedIndex;
            allIDS[index].Owner = (string)values[2];
            allIDS[index].Description = (string)values[3];
            allIDS[index].Extra = (string)values[4];
            populateListView(viewSpreadsheetListView, allIDS);
            updateCells(spreadsheetIDTextBox.Text, $"ids!a{index + 2}:e{index + 2}", values);
        }

        //TODO: Implement scanning
        private async void rescanAssignIDsButton_Click(object sender, RoutedEventArgs e)
        {
            var active_tag = await RFIDScanner.Scan(rfid_scanner_client, rfid_scanner_options);
            activeTagTextbox.Text = active_tag.EPC;
            var index = allIDS.FindIndex(x => x.EPC == active_tag.EPC);
            if (index > -1) viewSpreadsheetListView.SelectedIndex = index;
        }

        /// <summary>
        /// Access spreadsheet through active sheet service with given ID and range
        /// </summary>
        /// <param name="spreadsheetID">Should match the regex: [-\w]{25,}</param>
        /// <param name="range">Use sheet name to get whole spreadsheet, otherwise specify using A1 notation</param>
        /// <returns></returns>
        private async Task<IList<IList<object>>> getValuesFromSpreadsheet(string spreadsheetID, string range)
        {
            SpreadsheetsResource.ValuesResource.GetRequest request = sheets_service.Spreadsheets.Values.Get(spreadsheetID, range);

            ValueRange response = await request.ExecuteAsync();
            return response.Values;
        }

        private void serviceLogin()
        {
            ServiceAccountCredential creds;
            string service_file = @"Assets\service_account.json";

            using (Stream stream = new FileStream(service_file, FileMode.Open, FileAccess.Read))
            {
                creds = (ServiceAccountCredential)GoogleCredential.FromStream(stream).UnderlyingCredential;
                var initializer = new ServiceAccountCredential.Initializer(creds.Id)
                {
                    User = service_email,
                    Key = creds.Key,
                    Scopes = Scopes
                };
                creds = new ServiceAccountCredential(initializer);
            }
            sheets_service = new SheetsService(new BaseClientService.Initializer()
            {
                HttpClientInitializer = creds,
                ApplicationName = AppName
            });
            logged_in = true;
            statusLabel.Content = "service";
            statusLabel.Foreground = new SolidColorBrush(Colors.Blue);
        }

        private void userLogin()
        {
            if (!shared)
            {
                UserCredential creds;
                using (var stream = new FileStream(@"Assets\credentials.json", FileMode.Open, FileAccess.Read))
                {
                    string tokenPath = @"Assets\token";
                    creds = GoogleWebAuthorizationBroker.AuthorizeAsync(
                        GoogleClientSecrets.Load(stream).Secrets,
                        Scopes,
                        "user",
                        CancellationToken.None,
                        new FileDataStore(tokenPath, true)).Result;
                }
                sheets_service = new SheetsService(new BaseClientService.Initializer()
                {
                    HttpClientInitializer = creds,
                    ApplicationName = AppName
                });
                drive_service = new DriveService(new BaseClientService.Initializer()
                {
                    HttpClientInitializer = creds,
                    ApplicationName = AppName
                });
            }

            logged_in = true;
            signInButton.IsEnabled = false;
            statusLabel.Content = "user";
            statusLabel.Foreground = new SolidColorBrush(Colors.Green);
        }

        private async void shareSpreadsheet(string spreadsheetID)
        {
            if (shared) return;
            var batch = new BatchRequest(drive_service);
            BatchRequest.OnResponse<Permission> callback = delegate (
                Permission permission,
                RequestError err,
                int index,
                System.Net.Http.HttpResponseMessage msg
            )
            {
                if (err != null)
                {
                    MessageBox.Show(err.Message);
                }
            };
            Permission usrPermission = new Permission()
            {
                Type = "user",
                Role = "writer",
                EmailAddress = service_email
            };
            var request = drive_service.Permissions.Create(usrPermission, spreadsheetID);
            request.SendNotificationEmail = false;
            request.Fields = "id";
            batch.Queue(request, callback);
            await batch.ExecuteAsync();
            Properties.Settings.Default.spreadsheetID = spreadsheetID;
            Properties.Settings.Default.Save();
        }

        private void appendNewRow(string spreadsheetID, string range, params object[] items)
        {
            IList<IList<object>> vals = new List<IList<object>>() { items };

            SpreadsheetsResource.ValuesResource.AppendRequest request = sheets_service.Spreadsheets.Values.Append(
                new ValueRange()
                {
                    Values = vals
                }, spreadsheetID, range);
            request.InsertDataOption = SpreadsheetsResource.ValuesResource.AppendRequest.InsertDataOptionEnum.INSERTROWS;
            request.ValueInputOption = SpreadsheetsResource.ValuesResource.AppendRequest.ValueInputOptionEnum.RAW;
            var response = request.Execute();
        }

        private void populateListView(ListView lv, List<ID> ids)
        {
            var gridView = new GridView();
            lv.View = gridView;
            gridView.Columns.Add(new GridViewColumn() { Header = "EPC", DisplayMemberBinding = new Binding("EPC") });
            gridView.Columns.Add(new GridViewColumn() { Header = "Status", DisplayMemberBinding = new Binding("Status") });
            gridView.Columns.Add(new GridViewColumn() { Header = "Owner", DisplayMemberBinding = new Binding("Owner") });
            gridView.Columns.Add(new GridViewColumn() { Header = "Description", DisplayMemberBinding = new Binding("Description") });
            gridView.Columns.Add(new GridViewColumn() { Header = "Extra", DisplayMemberBinding = new Binding("Extra") });
            lv.ItemsSource = ids;
        }

        private void populateListView(ListView lv, List<Log> log)
        {
            var gridView = new GridView();
            lv.View = gridView;
            gridView.Columns.Add(new GridViewColumn() { Header = "Timestamp", DisplayMemberBinding = new Binding("TimeStamp") });
            gridView.Columns.Add(new GridViewColumn() { Header = "Status", DisplayMemberBinding = new Binding("Status") });
            gridView.Columns.Add(new GridViewColumn() { Header = "EPC", DisplayMemberBinding = new Binding("EPC") });
            gridView.Columns.Add(new GridViewColumn() { Header = "Owner", DisplayMemberBinding = new Binding("Owner") });
            gridView.Columns.Add(new GridViewColumn() { Header = "Description", DisplayMemberBinding = new Binding("Description") });
            gridView.Columns.Add(new GridViewColumn() { Header = "Extra", DisplayMemberBinding = new Binding("Extra") });
            lv.ItemsSource = log;
        }

        private async void updateCells(string spreadsheetID, string range, IList<object> value)
        {
            updateRowPictureBox.Visibility = Visibility.Visible;
            var list = new List<IList<object>> { value };
            var req = sheets_service.Spreadsheets.Values.Update(new ValueRange
            {
                Values = list,
            }, spreadsheetID, range);
            req.ValueInputOption = SpreadsheetsResource.ValuesResource.UpdateRequest.ValueInputOptionEnum.RAW;
            await req.ExecuteAsync();
            updateRowPictureBox.Visibility = Visibility.Hidden;
        }

        private async void starStopServiceButton_Click(object sender, RoutedEventArgs e)
        {
            logging = !logging;
            if (logging)
            {
                serviceLabel.Content = "starting";
                serviceLabel.Foreground = new SolidColorBrush(Colors.Blue);

                await RFIDScanner.Log((tags) =>
                {
                    foreach (var tag in tags)
                    {
                        var index = allIDS.FindIndex(id => id.EPC == tag.EPC);
                        if (index == -1) continue;
                        var log = new Log(tag.Timestamp, tag.Status, tag.EPC, allIDS[index].Owner, allIDS[index].Description, allIDS[index].Extra);

                        allLogs.Add(log);
                        appendNewRow(Properties.Settings.Default.spreadsheetID, "log", log.TimeStamp, log.Status, log.EPC, log.Owner, log.Description, log.Extra);
                        populateListView(logSpreadsheetListView, allLogs);
                    }
                }, rfid_scanner_client, rfid_scanner_options);
                serviceLabel.Content = "logging";
                serviceLabel.Foreground = new SolidColorBrush(Colors.Green);
            } else
            {
                serviceLabel.Content = "stopping";
                serviceLabel.Foreground = new SolidColorBrush(Colors.Blue);
                RFIDScanner.Dispose(rfid_scanner_client);
                serviceLabel.Content = "stopped";
                serviceLabel.Foreground = new SolidColorBrush(Colors.Red);
            }
        }
    }

    public class ID
    {
        public string EPC { get; set; }
        public Status Status { get; set; }
        public string Owner { get; set; }
        public string Description { get; set; }
        public string Extra { get; set; }

        public ID(string epc, Status status, string owner, string description, string extra = "")
        {
            EPC = epc;
            Status = status;
            Owner = owner;
            Description = description;
            Extra = extra;
        }
    }

    public class Log
    {
        public DateTime TimeStamp { get; set; }
        public Status Status { get; set; }
        public string EPC { get; set; }
        public string Owner { get; set; }
        public string Description { get; set; }
        public string Extra { get; set; }

        public Log(DateTime timeStamp, Status status, string epc, string owner, string description, string extra = "")
        {
            TimeStamp = timeStamp;
            Status = status;
            EPC = epc;
            Owner = owner;
            Description = description;
            Extra = extra;
        }
    }

    public enum Status
    {
        In = 0,
        Out = 1
    }
}
