using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;

namespace Mrea.SolidWorksCadAgent
{
    internal static class Program
    {
        private const string ProtocolVersion = "mrea.solidworks-agent.v1";
        private const string AdapterName = "SOLIDWORKS_2026";
        private const string WorkerCapabilitiesSha256 = "1713a8671cc358c54af5664fb1144789ba85b50291d2b02e479aa568a14ae4bd";
        private const string ConstraintCapabilitiesSha256 = "02a33af48298669e3563ce467b6cd6d8f2586d073baa3de6baa45749fc92a3d8";

        private const int ExitSuccess = 0;
        private const int ExitInvalidInput = 20;
        private const int ExitSolidWorksStartup = 30;
        private const int ExitCadTransfer = 40;
        private const int ExitArtifact = 50;
        private const int ExitUnexpected = 70;

        [STAThread]
        private static int Main(string[] args)
        {
            string requestPath = null;
            string responsePath = null;

            try
            {
                ParseArguments(args, out requestPath, out responsePath);
            }
            catch (Exception exc)
            {
                Console.Error.WriteLine(exc);
                return ExitInvalidInput;
            }

            AgentRequest request;
            try
            {
                var serializer = NewSerializer();
                request = serializer.Deserialize<AgentRequest>(File.ReadAllText(requestPath, Encoding.UTF8));
                ValidateRequestEnvelope(request);
            }
            catch (Exception exc)
            {
                SafeWriteFailure(
                    responsePath,
                    exc,
                    ExitInvalidInput,
                    "REQUEST_INVALID",
                    "AGENT_STARTUP",
                    false,
                    null);
                Console.Error.WriteLine(exc);
                return ExitInvalidInput;
            }

            SolidWorksSession session = null;
            try
            {
                try
                {
                    session = SolidWorksSession.Open(request);
                }
                catch (Exception exc)
                {
                    SafeWriteFailure(
                        responsePath,
                        exc,
                        ExitSolidWorksStartup,
                        StartupFailureCode(exc),
                        "SOLIDWORKS_COM",
                        false,
                        null);
                    Console.Error.WriteLine(exc);
                    return ExitSolidWorksStartup;
                }

                AgentResponse response;
                try
                {
                    response = SolidWorksTransfer.Execute(session, request);
                }
                catch (IOException exc)
                {
                    SafeWriteFailure(
                        responsePath,
                        exc,
                        ExitArtifact,
                        "ARTIFACT_WRITE_FAILED",
                        "ARTIFACT",
                        true,
                        session.Version);
                    Console.Error.WriteLine(exc);
                    return ExitArtifact;
                }
                catch (COMException exc)
                {
                    SafeWriteFailure(
                        responsePath,
                        exc,
                        ExitCadTransfer,
                        "SOLIDWORKS_COM_TRANSFER_FAILED",
                        "CAD_TRANSFER",
                        true,
                        session.Version);
                    Console.Error.WriteLine(exc);
                    return ExitCadTransfer;
                }
                catch (Exception exc)
                {
                    SafeWriteFailure(
                        responsePath,
                        exc,
                        ExitCadTransfer,
                        "CAD_TRANSFER_FAILED",
                        "CAD_TRANSFER",
                        true,
                        session.Version);
                    Console.Error.WriteLine(exc);
                    return ExitCadTransfer;
                }

                response.real_host_executed = true;
                response.solidworks_version = session.Version;
                response.exit_code = ExitSuccess;
                response.diagnostics = response.diagnostics ?? new List<DiagnosticDto>();

                try
                {
                    WriteResponse(responsePath, response);
                }
                catch (Exception exc)
                {
                    Console.Error.WriteLine(exc);
                    return ExitArtifact;
                }
                return ExitSuccess;
            }
            catch (Exception exc)
            {
                SafeWriteFailure(
                    responsePath,
                    exc,
                    ExitUnexpected,
                    "AGENT_INTERNAL_FAILURE",
                    "INTERNAL",
                    session != null,
                    session != null ? session.Version : null);
                Console.Error.WriteLine(exc);
                return ExitUnexpected;
            }
            finally
            {
                if (session != null)
                    session.Dispose();
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
            if (!string.Equals(
                request.worker_capabilities_sha256,
                WorkerCapabilitiesSha256,
                StringComparison.Ordinal))
                throw new InvalidDataException(
                    "Worker capability fingerprint mismatch; expected=" +
                    WorkerCapabilitiesSha256 +
                    " actual=" +
                    (request.worker_capabilities_sha256 ?? "<missing>"));
            if (!string.Equals(
                request.constraint_capabilities_sha256,
                ConstraintCapabilitiesSha256,
                StringComparison.Ordinal))
                throw new InvalidDataException(
                    "Constraint capability fingerprint mismatch; expected=" +
                    ConstraintCapabilitiesSha256 +
                    " actual=" +
                    (request.constraint_capabilities_sha256 ?? "<missing>"));
            if (string.IsNullOrWhiteSpace(request.sketch_package_id))
                throw new InvalidDataException("sketch_package_id is required.");
            if (string.IsNullOrWhiteSpace(request.output_directory))
                throw new InvalidDataException("output_directory is required.");
            request.entities = request.entities ?? new List<EntitySpec>();
            request.constraints = request.constraints ?? new List<ConstraintSpec>();
            request.dimensions = request.dimensions ?? new List<DimensionSpec>();
        }

        private static string StartupFailureCode(Exception exc)
        {
            var message = exc.Message ?? string.Empty;
            if (message.IndexOf("version mismatch", StringComparison.OrdinalIgnoreCase) >= 0 ||
                message.IndexOf("RevisionNumber", StringComparison.OrdinalIgnoreCase) >= 0)
                return "SOLIDWORKS_VERSION_UNSUPPORTED";
            if (message.IndexOf("ProgID", StringComparison.OrdinalIgnoreCase) >= 0 ||
                message.IndexOf("not registered", StringComparison.OrdinalIgnoreCase) >= 0)
                return "SOLIDWORKS_COM_NOT_REGISTERED";
            if (message.IndexOf("template", StringComparison.OrdinalIgnoreCase) >= 0)
                return "PART_TEMPLATE_UNAVAILABLE";
            return "SOLIDWORKS_STARTUP_FAILED";
        }

        private static AgentResponse FailureResponse(
            Exception exc,
            int exitCode,
            string code,
            string stage,
            bool realHostExecuted,
            string solidWorksVersion)
        {
            var details = new Dictionary<string, object>
            {
                { "exception_type", exc.GetType().FullName }
            };
            var diagnostic = new DiagnosticDto
            {
                code = code,
                stage = stage,
                message = exc.Message,
                severity = "ERROR",
                details = details
            };
            return new AgentResponse
            {
                protocol_version = ProtocolVersion,
                status = "ERROR",
                adapter_name = AdapterName,
                real_host_executed = realHostExecuted,
                solidworks_version = solidWorksVersion,
                exit_code = exitCode,
                bindings = new List<DimensionBindingDto>(),
                read_back = new ReadBackDto
                {
                    dimensions = new List<ReadBackDimensionDto>(),
                    constraint_conflicts = new List<string>()
                },
                artifacts = new List<ArtifactDto>(),
                diagnostics = new List<DiagnosticDto> { diagnostic },
                error = new ErrorDto
                {
                    type = exc.GetType().FullName,
                    code = code,
                    stage = stage,
                    message = exc.Message,
                    severity = "ERROR",
                    details = details
                }
            };
        }

        private static void SafeWriteFailure(
            string responsePath,
            Exception exc,
            int exitCode,
            string code,
            string stage,
            bool realHostExecuted,
            string solidWorksVersion)
        {
            if (string.IsNullOrWhiteSpace(responsePath))
                return;
            try
            {
                WriteResponse(
                    responsePath,
                    FailureResponse(
                        exc,
                        exitCode,
                        code,
                        stage,
                        realHostExecuted,
                        solidWorksVersion));
            }
            catch
            {
                // Exit code and stderr remain the final failure signal if response writing also fails.
            }
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
