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
            ValidateRequest(request);
            Directory.CreateDirectory(request.output_directory);

            dynamic model = session.Model;
            dynamic sketchManager = model.SketchManager;
            dynamic activeSketch = sketchManager.ActiveSketch;
            if (activeSketch == null)
                throw new InvalidOperationException("SOLIDWORKS has no active sketch for transfer.");

            var entitySpecs = request.entities.ToDictionary(item => item.entity_id, StringComparer.Ordinal);
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

            ApplyConstraints(activeSketch, entitySpecs, entities, request.constraints);

            foreach (var dimension in request.dimensions)
            {
                dynamic modelDimension = CreateDimension(model, entities, entitySpecs, dimension);
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

            if (!model.EditRebuild3())
                throw new InvalidOperationException("SOLIDWORKS EditRebuild3 failed after CAD transfer.");

            var constraintConflicts = DetectConstraintConflicts(activeSketch, request.dimensions);

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

            sketchManager.InsertSketch(true);
            if (!model.EditRebuild3())
                throw new InvalidOperationException("SOLIDWORKS EditRebuild3 failed after leaving the sketch.");

            var outputPath = Path.Combine(
                Path.GetFullPath(request.output_directory),
                SafeFileName(request.sketch_package_id) + ".SLDPRT");
            SaveNativePart(model, outputPath);

            return new AgentResponse
            {
                protocol_version = ProtocolVersion,
                status = "OK",
                adapter_name = AdapterName,
                bindings = bindings,
                read_back = new ReadBackDto
                {
                    dimensions = readBack,
                    constraint_conflicts = constraintConflicts
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

        internal static void ValidateRequest(AgentRequest request)
        {
            var ids = new HashSet<string>(StringComparer.Ordinal);
            var entitySpecs = new Dictionary<string, EntitySpec>(StringComparer.Ordinal);
            foreach (var entity in request.entities)
            {
                if (entity == null || string.IsNullOrWhiteSpace(entity.entity_id))
                    throw new InvalidDataException("Every entity requires entity_id.");
                if (!ids.Add(entity.entity_id))
                    throw new InvalidDataException("Duplicate entity_id: " + entity.entity_id);
                if (entity.type != "POINT" && entity.type != "LINE" && entity.type != "CIRCLE" && entity.type != "ARC")
                    throw new NotSupportedException("Unsupported SOLIDWORKS entity type: " + entity.type);
                entitySpecs.Add(entity.entity_id, entity);
            }

            var constraintIds = new HashSet<string>(StringComparer.Ordinal);
            foreach (var constraint in request.constraints)
            {
                if (constraint == null || string.IsNullOrWhiteSpace(constraint.constraint_id))
                    throw new InvalidDataException("Every constraint requires constraint_id.");
                if (!constraintIds.Add(constraint.constraint_id))
                    throw new InvalidDataException("Duplicate constraint_id: " + constraint.constraint_id);
                if (constraint.status == "UNRESOLVED")
                    throw new NotSupportedException(
                        "UNRESOLVED canonical constraint must not be transferred: " + constraint.constraint_id);
                if (constraint.entity_ids == null || constraint.entity_ids.Count == 0)
                    throw new InvalidDataException("Constraint has no entity_ids: " + constraint.constraint_id);
                foreach (var entityId in constraint.entity_ids)
                    if (!ids.Contains(entityId))
                        throw new InvalidDataException("Constraint references unknown entity: " + entityId);

                ValidateConstraintShape(constraint, entitySpecs);
            }

            var dimensionIds = new HashSet<string>(StringComparer.Ordinal);
            foreach (var dimension in request.dimensions)
            {
                if (dimension == null || string.IsNullOrWhiteSpace(dimension.dimension_id))
                    throw new InvalidDataException("Every verified dimension requires dimension_id.");
                if (!dimensionIds.Add(dimension.dimension_id))
                    throw new InvalidDataException("Duplicate dimension_id: " + dimension.dimension_id);
                if (dimension.type != "DISTANCE" && dimension.type != "DIAMETER" && dimension.type != "RADIUS")
                {
                    if (dimension.type == "ANGLE")
                        throw new NotSupportedException(
                            "ANGLE transfer is intentionally blocked: SketchPackage v1 does not identify the angular branch/quadrant required for deterministic SOLIDWORKS placement.");
                    throw new NotSupportedException("Unsupported SOLIDWORKS dimension type: " + dimension.type);
                }
                if (dimension.unit != "mm")
                    throw new NotSupportedException(
                        "DISTANCE/DIAMETER/RADIUS require canonical mm in the current SOLIDWORKS worker: " +
                        dimension.dimension_id + " unit=" + dimension.unit);
                if (dimension.entity_ids == null || dimension.entity_ids.Count == 0)
                    throw new InvalidDataException("Dimension has no entity_ids: " + dimension.dimension_id);
                foreach (var entityId in dimension.entity_ids)
                    if (!ids.Contains(entityId))
                        throw new InvalidDataException("Dimension references unknown entity: " + entityId);
            }
        }

        private static dynamic CreateEntity(dynamic sketchManager, EntitySpec entity)
        {
            if (entity.type == "POINT")
            {
                RequirePoint(entity.point, entity.entity_id + ".point");
                dynamic point = sketchManager.CreatePoint(
                    MmToM(entity.point.x), MmToM(entity.point.y), 0.0);
                if (point == null)
                    throw new InvalidOperationException("CreatePoint failed for " + entity.entity_id);
                return point;
            }

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
                RequirePositiveFinite(entity.radius, entity.entity_id + ".radius");
                dynamic segment = sketchManager.CreateCircleByRadius(
                    MmToM(entity.center.x), MmToM(entity.center.y), 0.0, MmToM(entity.radius));
                if (segment == null)
                    throw new InvalidOperationException("CreateCircleByRadius failed for " + entity.entity_id);
                return segment;
            }

            if (entity.type == "ARC")
            {
                RequirePoint(entity.center, entity.entity_id + ".center");
                RequirePositiveFinite(entity.radius, entity.entity_id + ".radius");
                RequireFinite(entity.start_angle_deg, entity.entity_id + ".start_angle_deg");
                RequireFinite(entity.end_angle_deg, entity.entity_id + ".end_angle_deg");

                var span = NormalizePositiveDegrees(entity.end_angle_deg - entity.start_angle_deg);
                if (span < 1e-12)
                    throw new InvalidDataException(
                        "ARC start/end angles describe a zero/full-circle span; use CIRCLE for full circles: " +
                        entity.entity_id);

                var startRad = entity.start_angle_deg * Math.PI / 180.0;
                var endRad = entity.end_angle_deg * Math.PI / 180.0;
                var startX = entity.center.x + entity.radius * Math.Cos(startRad);
                var startY = entity.center.y + entity.radius * Math.Sin(startRad);
                var endX = entity.center.x + entity.radius * Math.Cos(endRad);
                var endY = entity.center.y + entity.radius * Math.Sin(endRad);

                dynamic segment = sketchManager.CreateArc(
                    MmToM(entity.center.x), MmToM(entity.center.y), 0.0,
                    MmToM(startX), MmToM(startY), 0.0,
                    MmToM(endX), MmToM(endY), 0.0,
                    (short)1);
                if (segment == null)
                    throw new InvalidOperationException("CreateArc failed for " + entity.entity_id);
                return segment;
            }

            throw new NotSupportedException("Unsupported entity type: " + entity.type);
        }

        private static void ApplyConstraints(
            dynamic activeSketch,
            IDictionary<string, EntitySpec> entitySpecs,
            IDictionary<string, dynamic> entities,
            IEnumerable<ConstraintSpec> constraints)
        {
            dynamic relationManager = activeSketch.RelationManager;
            if (relationManager == null)
                throw new InvalidOperationException("SOLIDWORKS did not expose the active sketch RelationManager.");

            foreach (var spec in constraints)
            {
                var relationEntities = spec.entity_ids
                    .Select(entityId => (object)entities[entityId])
                    .ToArray();
                var relationType = ConstraintType(spec, entitySpecs);

                dynamic relation = relationManager.AddRelation(relationEntities, relationType);
                if (relation == null)
                    throw new InvalidOperationException(
                        "SOLIDWORKS failed to create constraint " + spec.constraint_id + " (" + spec.type + ").");
            }
        }

        private static int ConstraintType(
            ConstraintSpec spec,
            IDictionary<string, EntitySpec> entitySpecs)
        {
            if (spec.type == "HORIZONTAL")
            {
                var types = spec.entity_ids.Select(id => entitySpecs[id].type).Distinct().ToArray();
                if (types.Length == 1 && types[0] == "LINE")
                    return (int)swConstraintType_e.swConstraintType_HORIZONTAL;
                if (types.Length == 1 && types[0] == "POINT" && spec.entity_ids.Count >= 2)
                    return (int)swConstraintType_e.swConstraintType_HORIZPOINTS;
            }

            if (spec.type == "VERTICAL")
            {
                var types = spec.entity_ids.Select(id => entitySpecs[id].type).Distinct().ToArray();
                if (types.Length == 1 && types[0] == "LINE")
                    return (int)swConstraintType_e.swConstraintType_VERTICAL;
                if (types.Length == 1 && types[0] == "POINT" && spec.entity_ids.Count >= 2)
                    return (int)swConstraintType_e.swConstraintType_VERTPOINTS;
            }

            if (spec.type == "PARALLEL")
                return (int)swConstraintType_e.swConstraintType_PARALLEL;
            if (spec.type == "PERPENDICULAR")
                return (int)swConstraintType_e.swConstraintType_PERPENDICULAR;
            if (spec.type == "TANGENT")
                return (int)swConstraintType_e.swConstraintType_TANGENT;
            if (spec.type == "CONCENTRIC")
                return (int)swConstraintType_e.swConstraintType_CONCENTRIC;
            if (spec.type == "EQUAL")
                return (int)swConstraintType_e.swConstraintType_SAMELENGTH;
            if (spec.type == "COINCIDENT")
                return (int)swConstraintType_e.swConstraintType_COINCIDENT;

            throw new NotSupportedException(
                "Constraint " + spec.constraint_id + " (" + spec.type + ") is not safely mappable to SOLIDWORKS.");
        }

        private static void ValidateConstraintShape(
            ConstraintSpec spec,
            IDictionary<string, EntitySpec> entitySpecs)
        {
            var types = spec.entity_ids.Select(id => entitySpecs[id].type).ToArray();

            if (spec.type == "HORIZONTAL" || spec.type == "VERTICAL")
            {
                if (types.All(type => type == "LINE"))
                    return;
                if (types.Length >= 2 && types.All(type => type == "POINT"))
                    return;
                throw ConstraintShapeError(spec, "requires LINE entity/entities or at least two POINT entities");
            }

            if (spec.type == "PARALLEL" || spec.type == "PERPENDICULAR")
            {
                if (types.Length == 2 && types.All(type => type == "LINE"))
                    return;
                throw ConstraintShapeError(spec, "requires exactly two LINE entities");
            }

            if (spec.type == "TANGENT")
            {
                if (types.Length == 2 &&
                    types.All(IsSegmentType) &&
                    types.Any(type => type == "CIRCLE" || type == "ARC"))
                    return;
                throw ConstraintShapeError(spec, "requires two sketch segments with at least one CIRCLE/ARC");
            }

            if (spec.type == "CONCENTRIC")
            {
                if (types.Length == 2 && types.All(type => type == "CIRCLE" || type == "ARC"))
                    return;
                throw ConstraintShapeError(spec, "requires exactly two CIRCLE/ARC entities");
            }

            if (spec.type == "EQUAL")
            {
                if (types.Length >= 2 && types.All(type => type == "LINE"))
                    return;
                if (types.Length >= 2 && types.All(type => type == "CIRCLE" || type == "ARC"))
                    return;
                throw ConstraintShapeError(spec, "requires two or more LINE entities or two or more CIRCLE/ARC entities");
            }

            if (spec.type == "COINCIDENT")
            {
                var pointCount = types.Count(type => type == "POINT");
                var curveCount = types.Count(type => IsSegmentType(type));
                if (types.Length == 2 && pointCount == 1 && curveCount == 1)
                    return;
                throw ConstraintShapeError(
                    spec,
                    "is only unambiguous for one explicit POINT plus one LINE/CIRCLE/ARC; line endpoint identity is absent from SketchPackage v1");
            }

            if (spec.type == "SYMMETRIC")
            {
                throw ConstraintShapeError(
                    spec,
                    "cannot be mapped deterministically because SketchPackage v1 does not identify which entity is the symmetry axis");
            }

            throw new NotSupportedException(
                "Unsupported canonical constraint type for SOLIDWORKS: " + spec.type);
        }

        private static Exception ConstraintShapeError(ConstraintSpec spec, string detail)
        {
            return new NotSupportedException(
                "Constraint " + spec.constraint_id + " (" + spec.type + ") " + detail + ".");
        }

        private static bool IsSegmentType(string type)
        {
            return type == "LINE" || type == "CIRCLE" || type == "ARC";
        }

        private static dynamic CreateDimension(
            dynamic model,
            IDictionary<string, dynamic> entities,
            IDictionary<string, EntitySpec> entitySpecs,
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
                var firstSpec = entitySpecs[spec.entity_ids[0]];
                var secondSpec = entitySpecs[spec.entity_ids[1]];
                if (!IsCircularType(firstSpec.type) || !IsCircularType(secondSpec.type))
                    throw new NotSupportedException(
                        "Two-entity DISTANCE currently means circle/arc center distance: " + spec.dimension_id);

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
                if (!IsCircularType(entitySpecs[spec.entity_ids[0]].type))
                    throw new NotSupportedException("DIAMETER requires a CIRCLE/ARC entity: " + spec.dimension_id);
                dynamic segment = entities[spec.entity_ids[0]];
                if (!segment.Select4(false, null))
                    throw new InvalidOperationException("Failed to select circle/arc for diameter " + spec.dimension_id);
                displayDimension = model.AddDiameterDimension2(0.015, 0.025, 0.0);
            }
            else if (spec.type == "RADIUS" && spec.entity_ids.Count == 1)
            {
                if (!IsCircularType(entitySpecs[spec.entity_ids[0]].type))
                    throw new NotSupportedException("RADIUS requires a CIRCLE/ARC entity: " + spec.dimension_id);
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

        private static List<string> DetectConstraintConflicts(
            dynamic activeSketch,
            IEnumerable<DimensionSpec> dimensions)
        {
            var status = (int)activeSketch.GetConstrainedStatus();
            if (status == (int)swConstrainedStatus_e.swOverConstrained ||
                status == (int)swConstrainedStatus_e.swNoSolution ||
                status == (int)swConstrainedStatus_e.swInvalidSolution)
            {
                return dimensions.Select(item => item.dimension_id).Distinct().ToList();
            }

            if (status == (int)swConstrainedStatus_e.swUnknownConstraint ||
                status == (int)swConstrainedStatus_e.swAutosolveOff)
            {
                throw new InvalidOperationException(
                    "SOLIDWORKS sketch solver status does not permit reliable constraint verification: " + status);
            }

            return new List<string>();
        }

        private static bool IsCircularType(string type)
        {
            return type == "CIRCLE" || type == "ARC";
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
            RequireFinite(point.x, name + ".x");
            RequireFinite(point.y, name + ".y");
        }

        private static void RequirePositiveFinite(double value, string name)
        {
            RequireFinite(value, name);
            if (!(value > 0.0))
                throw new InvalidDataException(name + " must be > 0.");
        }

        private static void RequireFinite(double value, string name)
        {
            if (double.IsNaN(value) || double.IsInfinity(value))
                throw new InvalidDataException(name + " must be finite.");
        }

        private static double NormalizePositiveDegrees(double value)
        {
            var normalized = value % 360.0;
            if (normalized < 0.0)
                normalized += 360.0;
            return normalized;
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
