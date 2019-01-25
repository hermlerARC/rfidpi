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

namespace RFID_Securty_Solution
{
    public static class RFIDScanner
    {
        private static readonly string status_topic = "reader/status";
        private static readonly string active_tag_topic = "reader/active_tag";

        public static async Task<LoggedTag> Scan(IMqttClient client, IMqttClientOptions options)
        {
            var active_tag = new LoggedTag();
            await client.ConnectAsync(options);
            await client.SubscribeAsync(active_tag_topic, MqttQualityOfServiceLevel.AtLeastOnce);
            
            client.ApplicationMessageReceived += (s, e) => {
                var json = Encoding.UTF8.GetString(e.ApplicationMessage.Payload);
                active_tag = JsonConvert.DeserializeObject<LoggedTag>(json);
            };

            await client.PublishAsync(status_topic, "read_once", MqttQualityOfServiceLevel.AtLeastOnce);

            SpinWait.SpinUntil(() => active_tag.EPC != null, 100);
            
            return active_tag;
        }

        public static async Task<IMqttClient> Log(Action<List<LoggedTag>> callback, IMqttClient client, IMqttClientOptions options)
        {
            var scannedTags = new List<LoggedTag>();
            await client.ConnectAsync(options);
            await client.SubscribeAsync(active_tag_topic, MqttQualityOfServiceLevel.AtLeastOnce);

            client.ApplicationMessageReceived += (s, e) =>
            {
                var json = Encoding.UTF8.GetString(e.ApplicationMessage.Payload);
                scannedTags = JsonConvert.DeserializeObject<List<LoggedTag>>(json);
                callback(scannedTags);
            };

            await client.PublishAsync(status_topic, "read", MqttQualityOfServiceLevel.AtLeastOnce);

            return client;

        }

        public static async void Dispose(IMqttClient client)
        {
            await client.PublishAsync(status_topic, "stop", MqttQualityOfServiceLevel.AtLeastOnce);
            await client.UnsubscribeAsync(active_tag_topic);
            await client.DisconnectAsync();
        }
    }

    public class LoggedTag
    {
        public string EPC { get; set; }
        public DateTime Timestamp { get; set; }
        public Status Status { get; set; }

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
