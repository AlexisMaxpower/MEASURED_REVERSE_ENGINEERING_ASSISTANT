using System.Collections.Generic;

namespace Mrea.SolidWorksCadAgent
{
    internal sealed class AgentRequest
    {
        public string protocol_version { get; set; }
        public string adapter_name { get; set; }
        public string constraint_capabilities_sha256 { get; set; }
        public string sketch_package_id { get; set; }
        public string output_directory { get; set; }
        public string part_template_path { get; set; }
        public bool attach_to_running { get; set; }
        public bool allow_launch { get; set; }
        public List<EntitySpec> entities { get; set; }
        public List<ConstraintSpec> constraints { get; set; }
        public List<DimensionSpec> dimensions { get; set; }
    }

    internal sealed class PointSpec
    {
        public double x { get; set; }
        public double y { get; set; }
    }

    internal sealed class EntitySpec
    {
        public string entity_id { get; set; }
        public string type { get; set; }
        public PointSpec point { get; set; }
        public PointSpec start { get; set; }
        public PointSpec end { get; set; }
        public PointSpec center { get; set; }
        public double radius { get; set; }
        public double start_angle_deg { get; set; }
        public double end_angle_deg { get; set; }
    }

    internal sealed class ConstraintSpec
    {
        public string constraint_id { get; set; }
        public string type { get; set; }
        public List<string> entity_ids { get; set; }
        public string status { get; set; }
    }

    internal sealed class DimensionSpec
    {
        public string dimension_id { get; set; }
        public string measurement_id { get; set; }
        public string type { get; set; }
        public double value { get; set; }
        public string unit { get; set; }
        public List<string> entity_ids { get; set; }
    }

    internal sealed class AgentResponse
    {
        public string protocol_version { get; set; }
        public string status { get; set; }
        public string adapter_name { get; set; }
        public bool real_host_executed { get; set; }
        public string solidworks_version { get; set; }
        public int exit_code { get; set; }
        public List<DimensionBindingDto> bindings { get; set; }
        public ReadBackDto read_back { get; set; }
        public List<ArtifactDto> artifacts { get; set; }
        public List<DiagnosticDto> diagnostics { get; set; }
        public ErrorDto error { get; set; }
    }

    internal sealed class DimensionBindingDto
    {
        public string dimension_id { get; set; }
        public string measurement_id { get; set; }
        public string vendor_dimension_ref { get; set; }
    }

    internal sealed class ReadBackDto
    {
        public List<ReadBackDimensionDto> dimensions { get; set; }
        public List<string> constraint_conflicts { get; set; }
    }

    internal sealed class ReadBackDimensionDto
    {
        public string dimension_id { get; set; }
        public double actual_value { get; set; }
        public string unit { get; set; }
    }

    internal sealed class ArtifactDto
    {
        public string artifact_id { get; set; }
        public string kind { get; set; }
        public string uri { get; set; }
        public string media_type { get; set; }
        public string sha256 { get; set; }
        public Dictionary<string, object> metadata { get; set; }
    }

    internal sealed class DiagnosticDto
    {
        public string code { get; set; }
        public string stage { get; set; }
        public string message { get; set; }
        public string severity { get; set; }
        public Dictionary<string, object> details { get; set; }
    }

    internal sealed class ErrorDto
    {
        public string type { get; set; }
        public string code { get; set; }
        public string stage { get; set; }
        public string message { get; set; }
        public string severity { get; set; }
        public Dictionary<string, object> details { get; set; }
    }
}
