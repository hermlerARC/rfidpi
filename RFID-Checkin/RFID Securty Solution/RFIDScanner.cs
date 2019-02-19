using System;
using System.Windows;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using MQTTnet;
using MQTTnet.Client;
using MQTTnet.Protocol;
using Newtonsoft.Json;
using System.Text.RegularExpressions;
using System.Collections.Generic;


namespace RFID_Securty_Solution
{
    public static class RFIDScanner
    {
        public static async Task<LoggedTag> Scan(IMqttClient client, IMqttClientOptions options, string readerID)
        {
            Dispose(client, new List<string> { readerID });
            var active_tag = new LoggedTag();
            await client.ConnectAsync(options);
            await client.SubscribeAsync($"reader/{readerID}/active_tag", MqttQualityOfServiceLevel.AtLeastOnce);
            
            client.ApplicationMessageReceived += (s, e) => {
                var json = Encoding.UTF8.GetString(e.ApplicationMessage.Payload);
                var tags = JsonConvert.DeserializeObject<List<LoggedTag>>(json);
                active_tag = JsonConvert.DeserializeObject<List<LoggedTag>>(json)[0];
            };

            await client.PublishAsync($"reader/{readerID}/status", "read_once", MqttQualityOfServiceLevel.AtLeastOnce);

            SpinWait.SpinUntil(() => active_tag.EPC != null, 1000);
            return active_tag;
        }

        public static async Task<IMqttClient> Log(Action<List<LoggedTag>, string> callback, IMqttClient client, IMqttClientOptions options, List<string> raspi_ids)
        {
            Dispose(client, raspi_ids);
            var scannedTags = new List<LoggedTag>();
            await client.ConnectAsync(options);
            foreach (var raspi_id in raspi_ids)
            {
                await client.SubscribeAsync($"reader/{raspi_id}/active_tag", MqttQualityOfServiceLevel.AtLeastOnce);
            }

            client.ApplicationMessageReceived += (s, e) =>
            {
                var json = Encoding.UTF8.GetString(e.ApplicationMessage.Payload);
                scannedTags = JsonConvert.DeserializeObject<List<LoggedTag>>(json);
                callback(scannedTags, Regex.Match(e.ApplicationMessage.Topic, @"\/(.+)\/").Groups[1].Value);
            };

            foreach (var raspi_id in raspi_ids)
                await client.PublishAsync($"reader/{raspi_id}/status", "read", MqttQualityOfServiceLevel.AtLeastOnce);

            return client;
        }

        public static async void Dispose(IMqttClient client, List<string> raspi_ids)
        {
            foreach (var rid in raspi_ids)
            {
                try
                {
                    await client.PublishAsync($"reader/{rid}/status", "stop", MqttQualityOfServiceLevel.AtLeastOnce);
                    await client.UnsubscribeAsync($"reader/{rid}/active_tag");
                } catch (Exception ex)
                {

                }
            }
            await client.DisconnectAsync();
        }
    }

    public class LoggedTag
    {
        public string EPC { get; set; }
        public DateTime Time { get; set; }
        public Status Status { get; set; }
        public string RSSI { get; set; }

        public LoggedTag() { }

        public LoggedTag(string epc, DateTime timestamp, Status status)
        {
            EPC = epc;
            Time = timestamp;
            Status = status;
        }

        public LoggedTag(string epc, DateTime timestamp, int status)
        {
            EPC = epc;
            Time = timestamp;
            Status = (Status)status;
        }

        [JsonConstructor]
        public LoggedTag(string epc, string time, int status, string rssi)
        {
            EPC = epc;
            Time = DateTime.Parse(time);
            Status = (Status)status;
            RSSI = rssi;
        }
    }
}
