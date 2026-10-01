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
        private const string WorkerCapabilitiesSha256 = "756c37d781e051f0f5b0285a451dc53d2d9d90e98ad3e7b4bfa94924d88dd974";
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
            ValidateDimensionEnvelope(request);
        }

        private static void ValidateDimensionEnvelope(AgentRequest request)
        {
            var entitySpecs = new Dictionary<string, EntitySpec>(StringComparer.Ordinal);
            foreach (var entity in request.entities)
            {
                if (entity == null || string.IsNullOrWhiteSpace(entity.entity_id))
                    throw new InvalidDataException("Every entity requires entity_id.");
                if (entitySpecs.ContainsKey(entity.entity_id))
                    throw new InvalidDataException("Duplicate entity_id: " + entity.entity_id);
                entitySpecs.Add(entity.entity_id, entity);
            }

            var dimensionIds = new HashSet<string>(StringComparer.Ordinal);
            foreach (var dimension in request.dimensions)
            {
                if (dimension == null || string.IsNullOrWhiteSpace(dimension.dimension_id))
                    throw new InvalidDataException("Every verified dimension requires dimension_id.");
                if (!dimensionIds.Add(dimension.dimension_id))
                    throw new InvalidDataException("Duplicate dimension_id: " + dimension.dimension_id);
                if (dimension.type != "DISTANCE" && dimension.type != "DIAMETER" && dimension.type != "RADIUS" && dimension.type != "ANGLE")
                    throw new NotSupportedException("Unsupported dimension type: " + dimension.type);
                if (dimension.entity_ids == null || dimension.entity_ids.Count == 0)
                    throw new InvalidDataException("Dimension has no entity_ids: " + dimension.dimension_id);

                var seenEntityIds = new HashSet<string>(StringComparer.Ordinal);
                foreach (var entityId in dimension.entity_ids)
                {
                    if (!seenEntityIds.Add(entityId))
                        throw new InvalidDataException("Dimension contains duplicate entity_ids: " + dimension.dimension_id);
                    if (!entitySpecs.ContainsKey(entityId))
                        throw new InvalidDataException("Dimension references unknown entity: " + entityId);
                }

                if (dimension.type == "DISTANCE")
                {
                    RequireDimensionUnit(dimension, "mm");
                    if (dimension.entity_ids.Count == 1 && entitySpecs[dimension.entity_ids[0]].type == "LINE")
                        continue;
                    if (dimension.entity_ids.Count == 2 &&
                        IsCircleOrArc(entitySpecs[dimension.entity_ids[0]]) &&
                        IsCircleOrArc(entitySpecs[dimension.entity_ids[1]]))
                        continue;
                    throw new NotSupportedException(
                        "DISTANCE supports one LINE or two CIRCLE/ARC entities: " + dimension.dimension_id);
                }

                if (dimension.type == "DIAMETER")
                {
                    RequireDimensionUnit(dimension, "mm");
                    if (dimension.entity_ids.Count == 1 && entitySpecs[dimension.entity_ids[0]].type == "CIRCLE")
                        continue;
                    throw new NotSupportedException(
                        "DIAMETER requires exactly one CIRCLE: " + dimension.dimension_id);
                }

                if (dimension.type == "RADIUS")
                {
                    RequireDimensionUnit(dimension, "mm");
                    if (dimension.entity_ids.Count == 1 && IsCircleOrArc(entitySpecs[dimension.entity_ids[0]]))
                        continue;
                    throw new NotSupportedException(
                        "RADIUS requires exactly one CIRCLE/ARC: " + dimension.dimension_id);
                }

                RequireDimensionUnit(dimension, "deg");
                if (!(dimension.value > 0.0 && dimension.value < 180.0))
                    throw new NotSupportedException(
                        "ANGLE dimension requires 0 < value < 180 deg: " + dimension.dimension_id);
                if (dimension.entity_ids.Count != 2 ||
                    entitySpecs[dimension.entity_ids[0]].type != "LINE" ||
                    entitySpecs[dimension.entity_ids[1]].type != "LINE")
                    throw new NotSupportedException(
                        "ANGLE dimension requires exactly two LINE entities: " + dimension.dimension_id);
                RequireAngularEnvelopeLinePair(
                    entitySpecs[dimension.entity_ids[0]],
                    entitySpecs[dimension.entity_ids[1]],
                    dimension.dimension_id);
            }
        }

        private static void RequireDimensionUnit(DimensionSpec dimension, string expectedUnit)
        {
            if (dimension.unit != expectedUnit)
                throw new NotSupportedException(
                    dimension.type + " dimension requires " + expectedUnit + ": " + dimension.dimension_id);
        }

        private static bool IsCircleOrArc(EntitySpec entity)
        {
            return entity != null && (entity.type == "CIRCLE" || entity.type == "ARC");
        }

        private static void RequireAngularEnvelopeLinePair(EntitySpec first, EntitySpec second, string dimensionId)
        {
            if (first == null || second == null || first.type != "LINE" || second.type != "LINE")
                throw new NotSupportedException("ANGLE dimension supports LINE/LINE only: " + dimensionId);
            if (first.start == null || first.end == null || second.start == null || second.end == null)
                throw new InvalidDataException("ANGLE dimension requires complete LINE geometry: " + dimensionId);

            var rX = first.end.x - first.start.x;
            var rY = first.end.y - first.start.y;
            var sX = second.end.x - second.start.x;
            var sY = second.end.y - second.start.y;
            if (!IsFinite(rX) || !IsFinite(rY) || !IsFinite(sX) || !IsFinite(sY))
                throw new InvalidDataException("ANGLE dimension requires finite LINE geometry: " + dimensionId);

            var cross = rX * sY - rY * sX;
            var scale = Math.Sqrt((rX * rX + rY * rY) * (sX * sX + sY * sY));
            if (!(scale > 0.0))
                throw new InvalidDataException("ANGLE dimension requires non-degenerate LINE entities: " + dimensionId);
            if (Math.Abs(cross) / scale < 1e-10)
                throw new NotSupportedException("ANGLE dimension requires non-parallel LINE entities: " + dimensionId);
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
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
