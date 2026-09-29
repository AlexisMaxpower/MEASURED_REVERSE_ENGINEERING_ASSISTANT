using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using SolidWorks.Interop.swconst;

namespace Mrea.SolidWorksCadAgent
{
    internal static class SolidWorksTransfer
    {
        private const string ProtocolVersion = "mrea.solidworks-agent.v1";
        private const string AdapterName = "SOLIDWORKS_2026";

        internal static AgentResponse Execute(SolidWorksSession session, AgentRequest request)
        {
            ValidateSlice(request);
            Directory.CreateDirectory(request.output_directory);

            dynamic model = session.Model;
            dynamic sketchManager = model.SketchManager;
            var entities = new Dictionary<string, dynamic>(StringComparer.Ordinal);
            var dimensions = new Dictionary<string, dynamic>(StringComparer.Ordinal);
            var bindings = new List<DimensionBindingDto>();

            sketchManager.AddToDB = true;
            try
            {
                foreach (var entity in request.entities)
                    entities.Add(entity.entity_id, CreateEntity(sketchManager, entity));
            }
            finally
            {
                sketchManager.AddToDB = false;
            }

            foreach (var dimension in request.dimensions)
            {
                dynamic modelDimension = CreateDimension(model, entities, dimension);
                var vendorName = SafeDimensionName(dimension.dimension_id);
                modelDimension.Name = vendorName;

                var setStatus = (int)modelDimension.SetSystemValue3(
                    ToSystemValue(dimension.value, dimension.unit),
                    (int)swSetValueInConfiguration_e.swSetValue_InThisConfiguration,
                    null);
                if (setStatus != (int)swSetValueReturnStatus_e.swSetValue_Successful)
                    throw new InvalidOperationException(
                        "Failed to set dimension " + dimension.dimension_id + "; SetSystemValue3 status=" + setStatus);

                dimensions.Add(dimension.dimension_id, modelDimension);
                bindings.Add(new DimensionBindingDto
                {
                    dimension_id = dimension.dimension_id,
                    measurement_id = dimension.measurement_id,
                    vendor_dimension_ref = Convert.ToString(modelDimension.FullName, CultureInfo.InvariantCulture)
                });
                model.ClearSelection2(true);
            }

            sketchManager.InsertSketch(true);
            model.EditRebuild3();

            var outputPath = Path.Combine(
                Path.GetFullPath(request.output_directory),
                SafeFileName(request.sketch_package_id) + ".SLDPRT");
            SaveNativePart(model, outputPath);

            var readBack = new List<ReadBackDimensionDto>();
            foreach (var spec in request.dimensions)
            {
                dynamic dimension = dimensions[spec.dimension_id];
                var raw = dimension.GetSystemValue3((int)swInConfigurationOpts_e.swThisConfiguration, null);
                var systemValue = FirstDouble(raw);
                readBack.Add(new ReadBackDimensionDto
                {
                    dimension_id = spec.dimension_id,
                    actual_value = FromSystemValue(systemValue, spec.unit),
                    unit = spec.unit
                });
            }

            foreach (var binding in bindings)
            {
                dynamic dimension = dimensions[binding.dimension_id];
                binding.vendor_dimension_ref = Convert.ToString(dimension.FullName, CultureInfo.InvariantCulture);
            }

            return new AgentResponse
            {
                protocol_version = ProtocolVersion,
                status = "OK",
                adapter_name = AdapterName,
                bindings = bindings,
                read_back = new ReadBackDto
                {
                    dimensions = readBack,
                    constraint_conflicts = new List<string>()
                },
                artifacts = new List<ArtifactDto>
                {
                    new ArtifactDto
                    {
                        artifact_id = "SWPART-" + request.sketch_package_id,
                        kind = "SOLIDWORKS_PART",
                        uri = new Uri(outputPath).AbsoluteUri,
                        media_type = "application/octet-stream",
                        sha256 = Sha256(outputPath),
                        metadata = new Dictionary<string, object>
                        {
                            { "adapter", AdapterName },
                            { "solidworks_major", 2026 },
                            { "native_extension", ".SLDPRT" }
                        }
                    }
                },
                error = null
            };
        }

        private static void ValidateSlice(AgentRequest request)
        {
            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (var entity in request.entities)
            {
                if (entity == null || string.IsNullOrWhiteSpace(entity.entity_id))
                    throw new InvalidDataException("Every entity requires entity_id.");
                if (!ids.Add(entity.entity_id))
                    throw new InvalidDataException("Duplicate entity_id: " + entity.entity_id);
                if (entity.type != "LINE" && entity.type != "CIRCLE")
                    throw new NotSupportedException("Pass 2 agent supports LINE/CIRCLE only: " + entity.type);
            }

            var dimensionIds = new HashSet<string>(StringComparer.Ordinal);
            foreach (var dimension in request.dimensions)
            {
                if (dimension == null || string.IsNullOrWhiteSpace(dimension.dimension_id))
                    throw new InvalidDataException("Every verified dimension requires dimension_id.");
                if (!dimensionIds.Add(dimension.dimension_id))
                    throw new InvalidDataException("Duplicate dimension_id: " + dimension.dimension_id);
                if (dimension.unit != "mm")
                    throw new NotSupportedException("Pass 2 real-host slice currently supports mm dimensions only: " + dimension.unit);
                if (dimension.type != "DISTANCE" && dimension.type != "DIAMETER" && dimension.type != "RADIUS")
                    throw new NotSupportedException("Unsupported Pass 2 dimension type: " + dimension.type);
                if (dimension.entity_ids == null || dimension.entity_ids.Count == 0)
                    throw new InvalidDataException("Dimension has no entity_ids: " + dimension.dimension_id);
                foreach (var entityId in dimension.entity_ids)
                    if (!ids.Contains(entityId))
                        throw new InvalidDataException("Dimension references unknown entity: " + entityId);
            }
        }

        private static dynamic CreateEntity(dynamic sketchManager, EntitySpec entity)
        {
            if (entity.type == "LINE")
            {
                RequirePoint(entity.start, entity.entity_id + ".start");
                RequirePoint(entity.end, entity.entity_id + ".end");
                dynamic segment = sketchManager.CreateLine(
                    MmToM(entity.start.x), MmToM(entity.start.y), 0.0,
                    MmToM(entity.end.x), MmToM(entity.end.y), 0.0);
                if (segment == null)
                    throw new InvalidOperationException("CreateLine failed for " + entity.entity_id);
                return segment;
            }

            if (entity.type == "CIRCLE")
            {
                RequirePoint(entity.center, entity.entity_id + ".center");
                if (!(entity.radius > 0.0))
                    throw new InvalidDataException("Circle radius must be > 0 for " + entity.entity_id);
                dynamic segment = sketchManager.CreateCircleByRadius(
                    MmToM(entity.center.x), MmToM(entity.center.y), 0.0, MmToM(entity.radius));
                if (segment == null)
                    throw new InvalidOperationException("CreateCircleByRadius failed for " + entity.entity_id);
                return segment;
            }

            throw new NotSupportedException("Unsupported entity type: " + entity.type);
        }

        private static dynamic CreateDimension(
            dynamic model,
            IDictionary<string, dynamic> entities,
            DimensionSpec spec)
        {
            model.ClearSelection2(true);
            dynamic displayDimension;

            if (spec.type == "DISTANCE" && spec.entity_ids.Count == 1)
            {
                dynamic segment = entities[spec.entity_ids[0]];
                if (!segment.Select4(false, null))
                    throw new InvalidOperationException("Failed to select entity for dimension " + spec.dimension_id);
                displayDimension = model.AddDimension2(0.01, 0.01, 0.0);
            }
            else if (spec.type == "DISTANCE" && spec.entity_ids.Count == 2)
            {
                dynamic firstArc = entities[spec.entity_ids[0]];
                dynamic secondArc = entities[spec.entity_ids[1]];
                dynamic firstCenter = firstArc.GetCenterPoint2();
                dynamic secondCenter = secondArc.GetCenterPoint2();
                if (firstCenter == null || secondCenter == null)
                    throw new InvalidOperationException("Center-distance dimension requires circle/arc entities: " + spec.dimension_id);
                if (!firstCenter.Select4(false, null) || !secondCenter.Select4(true, null))
                    throw new InvalidOperationException("Failed to select centers for dimension " + spec.dimension_id);
                displayDimension = model.AddDimension2(0.04, 0.03, 0.0);
            }
            else if (spec.type == "DIAMETER" && spec.entity_ids.Count == 1)
            {
                dynamic segment = entities[spec.entity_ids[0]];
                if (!segment.Select4(false, null))
                    throw new InvalidOperationException("Failed to select circle for diameter " + spec.dimension_id);
                displayDimension = model.AddDiameterDimension2(0.015, 0.025, 0.0);
            }
            else if (spec.type == "RADIUS" && spec.entity_ids.Count == 1)
            {
                dynamic segment = entities[spec.entity_ids[0]];
                if (!segment.Select4(false, null))
                    throw new InvalidOperationException("Failed to select arc/circle for radius " + spec.dimension_id);
                displayDimension = model.AddRadialDimension2(0.015, 0.025, 0.0);
            }
            else
            {
                throw new NotSupportedException(
                    "Unsupported dimension/entity combination: " + spec.dimension_id + " " + spec.type);
            }

            if (displayDimension == null)
                throw new InvalidOperationException("SOLIDWORKS did not create dimension " + spec.dimension_id);
            dynamic modelDimension = displayDimension.GetDimension2(0);
            if (modelDimension == null)
                throw new InvalidOperationException("SOLIDWORKS did not expose model dimension for " + spec.dimension_id);
            return modelDimension;
        }

        private static void SaveNativePart(dynamic model, string outputPath)
        {
            int errors = 0;
            int warnings = 0;
            dynamic extension = model.Extension;
            bool saved = extension.SaveAs(
                outputPath,
                (int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                (int)swSaveAsOptions_e.swSaveAsOptions_Silent,
                null,
                ref errors,
                ref warnings);
            if (!saved || errors != 0)
                throw new IOException(
                    "SOLIDWORKS SaveAs failed; success=" + saved + ", errors=" + errors + ", warnings=" + warnings);
        }

        private static string SafeDimensionName(string dimensionId)
        {
            var builder = new StringBuilder("MREA_");
            foreach (var ch in dimensionId ?? string.Empty)
                builder.Append(char.IsLetterOrDigit(ch) ? ch : '_');
            return builder.ToString();
        }

        private static string SafeFileName(string value)
        {
            var invalid = new HashSet<char>(Path.GetInvalidFileNameChars());
            var chars = (value ?? "mrea-part").Select(ch => invalid.Contains(ch) ? '_' : ch).ToArray();
            return new string(chars);
        }

        private static void RequirePoint(PointSpec point, string name)
        {
            if (point == null)
                throw new InvalidDataException(name + " is required.");
            if (double.IsNaN(point.x) || double.IsInfinity(point.x) || double.IsNaN(point.y) || double.IsInfinity(point.y))
                throw new InvalidDataException(name + " must contain finite coordinates.");
        }

        private static double ToSystemValue(double value, string unit)
        {
            if (unit == "mm") return MmToM(value);
            if (unit == "deg") return value * Math.PI / 180.0;
            throw new NotSupportedException("Unsupported canonical unit: " + unit);
        }

        private static double FromSystemValue(double value, string unit)
        {
            if (unit == "mm") return value * 1000.0;
            if (unit == "deg") return value * 180.0 / Math.PI;
            throw new NotSupportedException("Unsupported canonical unit: " + unit);
        }

        private static double MmToM(double value) { return value / 1000.0; }

        private static double FirstDouble(object raw)
        {
            if (raw is double) return (double)raw;
            var array = raw as Array;
            if (array != null && array.Length > 0)
                return Convert.ToDouble(array.GetValue(0), CultureInfo.InvariantCulture);
            return Convert.ToDouble(raw, CultureInfo.InvariantCulture);
        }

        private static string Sha256(string path)
        {
            using (var stream = File.OpenRead(path))
            using (var sha = SHA256.Create())
                return string.Concat(sha.ComputeHash(stream).Select(b => b.ToString("x2", CultureInfo.InvariantCulture)));
        }
    }
}
