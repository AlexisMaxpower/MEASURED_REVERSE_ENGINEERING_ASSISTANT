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
            var entitySpecs = request.entities.ToDictionary(item => item.entity_id, item => item, StringComparer.Ordinal);
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

            ApplyConstraints(
                model,
                entities,
                entitySpecs,
                request.constraints ?? new List<ConstraintSpec>());

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
            var entitySpecs = new Dictionary<string, EntitySpec>(StringComparer.Ordinal);
            foreach (var entity in request.entities)
            {
                if (entity == null || string.IsNullOrWhiteSpace(entity.entity_id))
                    throw new InvalidDataException("Every entity requires entity_id.");
                if (entitySpecs.ContainsKey(entity.entity_id))
                    throw new InvalidDataException("Duplicate entity_id: " + entity.entity_id);
                entitySpecs.Add(entity.entity_id, entity);
                if (entity.type != "POINT" && entity.type != "LINE" && entity.type != "CIRCLE" && entity.type != "ARC")
                    throw new NotSupportedException("Vendor agent supports POINT/LINE/CIRCLE/ARC only: " + entity.type);

                if (entity.type == "POINT")
                    RequirePoint(entity.point, entity.entity_id + ".point");
                else if (entity.type == "LINE")
                {
                    RequirePoint(entity.start, entity.entity_id + ".start");
                    RequirePoint(entity.end, entity.entity_id + ".end");
                    RequireNonDegenerateLine(entity, entity.entity_id);
                }
                else if (entity.type == "CIRCLE")
                {
                    RequirePoint(entity.center, entity.entity_id + ".center");
                    RequirePositiveFinite(entity.radius, entity.entity_id + ".radius");
                }
                else if (entity.type == "ARC")
                {
                    RequirePoint(entity.center, entity.entity_id + ".center");
                    RequirePositiveFinite(entity.radius, entity.entity_id + ".radius");
                    RequireFinite(entity.start_angle_deg, entity.entity_id + ".start_angle_deg");
                    RequireFinite(entity.end_angle_deg, entity.entity_id + ".end_angle_deg");
                    var span = PositiveModulo(entity.end_angle_deg - entity.start_angle_deg, 360.0);
                    if (span < 1e-12)
                        throw new InvalidDataException(
                            "ARC start/end angles resolve to a full/zero circle; use CIRCLE instead: " + entity.entity_id);
                }
            }

            foreach (var constraint in request.constraints ?? new List<ConstraintSpec>())
                ValidateConstraint(constraint, entitySpecs);

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
                foreach (var entityId in dimension.entity_ids)
                    if (!entitySpecs.ContainsKey(entityId))
                        throw new InvalidDataException("Dimension references unknown entity: " + entityId);

                if (dimension.type == "ANGLE")
                {
                    if (dimension.unit != "deg")
                        throw new NotSupportedException("ANGLE dimension requires deg: " + dimension.dimension_id);
                    if (!(dimension.value > 0.0 && dimension.value < 180.0))
                        throw new NotSupportedException("ANGLE dimension requires 0 < value < 180 deg: " + dimension.dimension_id);
                    if (dimension.entity_ids.Count != 2)
                        throw new NotSupportedException("ANGLE dimension requires exactly two LINE entities: " + dimension.dimension_id);
                    if (entitySpecs[dimension.entity_ids[0]].type != "LINE" || entitySpecs[dimension.entity_ids[1]].type != "LINE")
                        throw new NotSupportedException("ANGLE dimension supports LINE/LINE only: " + dimension.dimension_id);
                    RequireAngularLinePair(entitySpecs[dimension.entity_ids[0]], entitySpecs[dimension.entity_ids[1]], dimension.dimension_id);
                }
                else if (dimension.unit != "mm")
                {
                    throw new NotSupportedException(
                        "Linear/radial real-host dimensions require mm: " + dimension.dimension_id + " unit=" + dimension.unit);
                }
            }
        }

        private static void ValidateConstraint(
            ConstraintSpec constraint,
            IDictionary<string, EntitySpec> entitySpecs)
        {
            if (constraint == null || string.IsNullOrWhiteSpace(constraint.constraint_id))
                throw new InvalidDataException("Every constraint requires constraint_id.");
            if (constraint.status != "VERIFIED")
                throw new NotSupportedException(
                    "Real-host constraint must be VERIFIED: " + constraint.constraint_id + " status=" + constraint.status);
            if (constraint.entity_ids == null || constraint.entity_ids.Count == 0)
                throw new InvalidDataException("Constraint has no entity_ids: " + constraint.constraint_id);
            if (constraint.entity_ids.Distinct(StringComparer.Ordinal).Count() != constraint.entity_ids.Count)
                throw new InvalidDataException("Constraint contains duplicate entity_ids: " + constraint.constraint_id);
            foreach (var entityId in constraint.entity_ids)
                if (!entitySpecs.ContainsKey(entityId))
                    throw new InvalidDataException("Constraint references unknown entity: " + entityId);

            if (constraint.type == "HORIZONTAL" || constraint.type == "VERTICAL")
            {
                if (constraint.entity_ids.Count != 1 || entitySpecs[constraint.entity_ids[0]].type != "LINE")
                    throw new NotSupportedException(constraint.type + " requires one LINE: " + constraint.constraint_id);
                return;
            }

            if (constraint.type == "PARALLEL" || constraint.type == "PERPENDICULAR" || constraint.type == "EQUAL")
            {
                if (constraint.entity_ids.Count != 2 ||
                    entitySpecs[constraint.entity_ids[0]].type != "LINE" ||
                    entitySpecs[constraint.entity_ids[1]].type != "LINE")
                    throw new NotSupportedException(constraint.type + " requires two LINE entities: " + constraint.constraint_id);
                return;
            }

            if (constraint.type == "CONCENTRIC")
            {
                if (constraint.entity_ids.Count != 2)
                    throw new NotSupportedException("CONCENTRIC requires two CIRCLE/ARC entities: " + constraint.constraint_id);
                foreach (var entityId in constraint.entity_ids)
                {
                    var type = entitySpecs[entityId].type;
                    if (type != "CIRCLE" && type != "ARC")
                        throw new NotSupportedException("CONCENTRIC requires two CIRCLE/ARC entities: " + constraint.constraint_id);
                }
                return;
            }

            throw new NotSupportedException(
                "Unsupported fail-closed canonical constraint type: " + constraint.type + " id=" + constraint.constraint_id);
        }

        private static void ApplyConstraints(
            dynamic model,
            IDictionary<string, dynamic> entities,
            IDictionary<string, EntitySpec> entitySpecs,
            IEnumerable<ConstraintSpec> constraints)
        {
            dynamic activeSketch = model.GetActiveSketch2();
            if (activeSketch == null)
                throw new InvalidOperationException("No active sketch while applying canonical constraints.");
            dynamic relationManager = activeSketch.RelationManager;
            if (relationManager == null)
                throw new InvalidOperationException("Active sketch did not expose RelationManager.");

            foreach (var constraint in constraints)
            {
                ValidateConstraint(constraint, entitySpecs);
                model.ClearSelection2(true);
                try
                {
                    for (var index = 0; index < constraint.entity_ids.Count; index++)
                    {
                        dynamic entity = entities[constraint.entity_ids[index]];
                        if (!entity.Select4(index > 0, null))
                            throw new InvalidOperationException(
                                "Failed to select entity for constraint " + constraint.constraint_id + ": " + constraint.entity_ids[index]);
                    }

                    var before = (int)relationManager.GetRelationsCount((int)swSketchRelationFilterType_e.swAll);
                    model.SketchAddConstraints(RelationId(constraint.type));
                    model.EditRebuild3();
                    var after = (int)relationManager.GetRelationsCount((int)swSketchRelationFilterType_e.swAll);
                    if (after <= before)
                        throw new InvalidOperationException(
                            "SOLIDWORKS did not create relation for constraint " + constraint.constraint_id);

                    var overDefining = (int)relationManager.GetRelationsCount(
                        (int)swSketchRelationFilterType_e.swOverDefining);
                    if (overDefining > 0)
                        throw new InvalidOperationException(
                            "Constraint caused an over-defining sketch: " + constraint.constraint_id);
                }
                finally
                {
                    model.ClearSelection2(true);
                }
            }
        }

        private static string RelationId(string constraintType)
        {
            switch (constraintType)
            {
                case "HORIZONTAL": return "sgHORIZONTAL2D";
                case "VERTICAL": return "sgVERTICAL2D";
                case "PARALLEL": return "sgPARALLEL";
                case "PERPENDICULAR": return "sgPERPENDICULAR";
                case "CONCENTRIC": return "sgCONCENTRIC";
                case "EQUAL": return "sgSAMELENGTH";
                default:
                    throw new NotSupportedException("Unsupported relation mapping: " + constraintType);
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
                RequireNonDegenerateLine(entity, entity.entity_id);
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

                var startRadians = entity.start_angle_deg * Math.PI / 180.0;
                var endRadians = entity.end_angle_deg * Math.PI / 180.0;
                var startX = entity.center.x + entity.radius * Math.Cos(startRadians);
                var startY = entity.center.y + entity.radius * Math.Sin(startRadians);
                var endX = entity.center.x + entity.radius * Math.Cos(endRadians);
                var endY = entity.center.y + entity.radius * Math.Sin(endRadians);

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
            else if (spec.type == "ANGLE" && spec.entity_ids.Count == 2)
            {
                var firstSpec = entitySpecs[spec.entity_ids[0]];
                var secondSpec = entitySpecs[spec.entity_ids[1]];
                RequireAngularLinePair(firstSpec, secondSpec, spec.dimension_id);
                dynamic firstLine = entities[spec.entity_ids[0]];
                dynamic secondLine = entities[spec.entity_ids[1]];
                if (!firstLine.Select4(false, null) || !secondLine.Select4(true, null))
                    throw new InvalidOperationException("Failed to select two lines for angle " + spec.dimension_id);
                var placement = AngularDimensionPlacement(firstSpec, secondSpec, spec.value);
                displayDimension = model.AddDimension2(MmToM(placement.x), MmToM(placement.y), 0.0);
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

        private static PointSpec AngularDimensionPlacement(EntitySpec first, EntitySpec second, double requestedAngleDeg)
        {
            RequireAngularLinePair(first, second, "ANGLE");

            var rX = first.end.x - first.start.x;
            var rY = first.end.y - first.start.y;
            var sX = second.end.x - second.start.x;
            var sY = second.end.y - second.start.y;
            var cross = rX * sY - rY * sX;
            if (Math.Abs(cross) < 1e-12)
                throw new NotSupportedException("ANGLE dimension requires non-parallel lines.");

            var qMinusPX = second.start.x - first.start.x;
            var qMinusPY = second.start.y - first.start.y;
            var t = (qMinusPX * sY - qMinusPY * sX) / cross;
            var intersectionX = first.start.x + t * rX;
            var intersectionY = first.start.y + t * rY;

            var rLength = Math.Sqrt(rX * rX + rY * rY);
            var sLength = Math.Sqrt(sX * sX + sY * sY);
            var uX = rX / rLength;
            var uY = rY / rLength;
            var vX = sX / sLength;
            var vY = sY / sLength;
            var dot = Math.Max(-1.0, Math.Min(1.0, uX * vX + uY * vY));
            var directedSectorDeg = Math.Acos(dot) * 180.0 / Math.PI;
            var supplementaryDeg = 180.0 - directedSectorDeg;

            var useSumBisector = Math.Abs(requestedAngleDeg - directedSectorDeg) <= Math.Abs(requestedAngleDeg - supplementaryDeg);
            var bisectorX = useSumBisector ? uX + vX : uX - vX;
            var bisectorY = useSumBisector ? uY + vY : uY - vY;
            var bisectorLength = Math.Sqrt(bisectorX * bisectorX + bisectorY * bisectorY);
            if (bisectorLength < 1e-12)
                throw new NotSupportedException("ANGLE dimension could not derive an unambiguous sector bisector.");

            bisectorX /= bisectorLength;
            bisectorY /= bisectorLength;
            var offsetMm = Math.Max(10.0, Math.Min(50.0, 0.25 * (rLength + sLength)));
            return new PointSpec
            {
                x = intersectionX + bisectorX * offsetMm,
                y = intersectionY + bisectorY * offsetMm
            };
        }

        private static void RequireAngularLinePair(EntitySpec first, EntitySpec second, string dimensionId)
        {
            if (first == null || second == null || first.type != "LINE" || second.type != "LINE")
                throw new NotSupportedException("ANGLE dimension supports LINE/LINE only: " + dimensionId);
            RequireNonDegenerateLine(first, first.entity_id);
            RequireNonDegenerateLine(second, second.entity_id);
            var rX = first.end.x - first.start.x;
            var rY = first.end.y - first.start.y;
            var sX = second.end.x - second.start.x;
            var sY = second.end.y - second.start.y;
            var cross = rX * sY - rY * sX;
            var scale = Math.Sqrt((rX * rX + rY * rY) * (sX * sX + sY * sY));
            if (scale <= 0.0 || Math.Abs(cross) / scale < 1e-10)
                throw new NotSupportedException("ANGLE dimension requires non-parallel LINE entities: " + dimensionId);
        }

        private static void RequireNonDegenerateLine(EntitySpec entity, string name)
        {
            var dx = entity.end.x - entity.start.x;
            var dy = entity.end.y - entity.start.y;
            if (dx * dx + dy * dy <= 1e-24)
                throw new InvalidDataException("LINE must have distinct endpoints: " + name);
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

        private static void RequireFinite(double value, string name)
        {
            if (double.IsNaN(value) || double.IsInfinity(value))
                throw new InvalidDataException(name + " must be finite.");
        }

        private static void RequirePositiveFinite(double value, string name)
        {
            RequireFinite(value, name);
            if (!(value > 0.0))
                throw new InvalidDataException(name + " must be > 0.");
        }

        private static double PositiveModulo(double value, double modulo)
        {
            var result = value % modulo;
            return result < 0.0 ? result + modulo : result;
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
