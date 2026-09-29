using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;

namespace Mrea.SolidWorksCadAgent
{
    internal static class Program
    {
        private const string ProtocolVersion = "mrea.solidworks-agent.v1";
        private const string AdapterName = "SOLIDWORKS_2026";

        [STAThread]
        private static int Main(string[] args)
        {
            string requestPath = null;
            string responsePath = null;
            try
            {
                ParseArguments(args, out requestPath, out responsePath);
                var serializer = NewSerializer();
                var request = serializer.Deserialize<AgentRequest>(File.ReadAllText(requestPath, Encoding.UTF8));
                ValidateRequestEnvelope(request);

                AgentResponse response;
                using (var session = SolidWorksSession.Open(request))
                {
                    response = SolidWorksTransfer.Execute(session, request);
                }

                WriteResponse(responsePath, response);
                return 0;
            }
            catch (Exception exc)
            {
                if (!string.IsNullOrWhiteSpace(responsePath))
                {
                    try
                    {
                        WriteResponse(responsePath, new AgentResponse
                        {
                            protocol_version = ProtocolVersion,
                            status = "ERROR",
                            adapter_name = AdapterName,
                            bindings = new List<DimensionBindingDto>(),
                            read_back = new ReadBackDto
                            {
                                dimensions = new List<ReadBackDimensionDto>(),
                                constraint_conflicts = new List<string>()
                            },
                            artifacts = new List<ArtifactDto>(),
                            error = new ErrorDto
                            {
                                type = exc.GetType().FullName,
                                message = exc.Message
                            }
                        });
                    }
                    catch
                    {
                        // The process exit code remains the final failure signal if response writing also fails.
                    }
                }
                Console.Error.WriteLine(exc);
                return 2;
            }
        }

        private static JavaScriptSerializer NewSerializer()
        {
            return new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        }

        private static void ParseArguments(string[] args, out string requestPath, out string responsePath)
        {
            requestPath = null;
            responsePath = null;
            for (var i = 0; i < args.Length; i++)
            {
                if (args[i] == "--request" && i + 1 < args.Length)
                {
                    requestPath = args[++i];
                }
                else if (args[i] == "--response" && i + 1 < args.Length)
                {
                    responsePath = args[++i];
                }
                else
                {
                    throw new ArgumentException("Unknown or incomplete argument: " + args[i]);
                }
            }

            if (string.IsNullOrWhiteSpace(requestPath) || string.IsNullOrWhiteSpace(responsePath))
            {
                throw new ArgumentException("Usage: Mrea.SolidWorksCadAgent.exe --request <request.json> --response <response.json>");
            }
        }

        private static void ValidateRequestEnvelope(AgentRequest request)
        {
            if (request == null)
                throw new InvalidDataException("Request JSON is empty.");
            if (request.protocol_version != ProtocolVersion)
                throw new InvalidDataException("Unsupported protocol_version: " + request.protocol_version);
            if (request.adapter_name != AdapterName)
                throw new InvalidDataException("Unsupported adapter_name: " + request.adapter_name);
            if (string.IsNullOrWhiteSpace(request.sketch_package_id))
                throw new InvalidDataException("sketch_package_id is required.");
            if (string.IsNullOrWhiteSpace(request.output_directory))
                throw new InvalidDataException("output_directory is required.");
            request.entities = request.entities ?? new List<EntitySpec>();
            request.dimensions = request.dimensions ?? new List<DimensionSpec>();
        }

        private static void WriteResponse(string path, AgentResponse response)
        {
            var directory = Path.GetDirectoryName(Path.GetFullPath(path));
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);
            File.WriteAllText(path, NewSerializer().Serialize(response), new UTF8Encoding(false));
        }
    }
}
