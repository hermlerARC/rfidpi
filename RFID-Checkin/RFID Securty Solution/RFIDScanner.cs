using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using MQTTnet;
using MQTTnet.Client;
using MQTTnet.Protocol;
using Newtonsoft.Json;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Collections.Specialized;

namespace RFID_Securty_Solution
{
    public static class RFIDScanner
    {
        public static async Task<LoggedTag> Scan(IMqttClient client, IMqttClientOptions options, string readerID)
        {
            var active_tag = new LoggedTag();
            await client.ConnectAsync(options);
            await client.SubscribeAsync($"reader/{readerID}/active_tag", MqttQualityOfServiceLevel.AtLeastOnce);
            
            client.ApplicationMessageReceived += (s, e) => {
                var json = Encoding.UTF8.GetString(e.ApplicationMessage.Payload);
                active_tag = JsonConvert.DeserializeObject<LoggedTag>(json);
            };

            await client.PublishAsync($"reader/{readerID}/status", "read_once", MqttQualityOfServiceLevel.AtLeastOnce);

            SpinWait.SpinUntil(() => active_tag.EPC != null, 100);
            
            return active_tag;
        }

        public static async Task<IMqttClient> Log(Action<List<LoggedTag>, List<String>> callback, IMqttClient client, IMqttClientOptions options, List<string> raspi_ids)
        {
            var scannedTags = new List<LoggedTag>();
            await client.ConnectAsync(options);
            foreach (var raspi_id in raspi_ids)
                await client.SubscribeAsync($"readers/{raspi_id}/active_tag", MqttQualityOfServiceLevel.AtLeastOnce);

            client.ApplicationMessageReceived += (s, e) =>
            {
                var json = Encoding.UTF8.GetString(e.ApplicationMessage.Payload);
                scannedTags = JsonConvert.DeserializeObject<List<LoggedTag>>(json);
                callback(scannedTags, raspi_ids);
            };

            foreach (var raspi_id in raspi_ids)
                await client.PublishAsync($"reader/{raspi_id}/status", "read", MqttQualityOfServiceLevel.AtLeastOnce);

            return client;
        }

        public static async void Dispose(IMqttClient client, List<string> raspi_ids)
        {
            foreach (var rid in raspi_ids)
            {
                await client.PublishAsync($"reader/{rid}/status", "stop", MqttQualityOfServiceLevel.AtLeastOnce);
                await client.UnsubscribeAsync($"reader/{rid}/active_tag");

            }
            await client.DisconnectAsync();
        }
    }

    public class LoggedTag
    {
        public string EPC { get; set; }
        public DateTime Timestamp { get; set; }
        public Status Status { get; set; }
        public string RSSI { get; set; }

        public LoggedTag() { }

        public LoggedTag(string epc, DateTime timestamp, Status status)
        {
            EPC = epc;
            Timestamp = timestamp;
            Status = status;
        }

        public LoggedTag(string epc, DateTime timestamp, int status)
        {
            EPC = epc;
            Timestamp = timestamp;
            Status = (Status)status;
        }

        [JsonConstructor]
        public LoggedTag(string epc, string timestamp, int status)
        {
            EPC = Regex.Match(epc, @"\'(.+)\'").Groups[1].Value;
            Timestamp = DateTime.Parse(timestamp);
            Status = (Status)status;
        }
    }
}
