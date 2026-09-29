from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Union
PrimitiveKind = Literal['LINE','CIRCLE','ARC']
ConstraintKind = Literal['HORIZONTAL','VERTICAL','PARALLEL','PERPENDICULAR','CONCENTRIC','EQUAL']
@dataclass(frozen=True, order=True)
class Point2D:
    x: float; y: float
    def to_dict(self): return {'x':float(self.x),'y':float(self.y)}
@dataclass(frozen=True)
class Line:
    entity_id:str; start:Point2D; end:Point2D; source:str='VISION_DETECTED'; confidence:float|None=None
    @property
    def kind(self)->PrimitiveKind:return 'LINE'
    @property
    def length(self)->float:return ((self.end.x-self.start.x)**2+(self.end.y-self.start.y)**2)**0.5
    def to_dict(self):return {'entity_id':self.entity_id,'kind':self.kind,'start':self.start.to_dict(),'end':self.end.to_dict(),'source':self.source,'confidence':self.confidence}
@dataclass(frozen=True)
class Circle:
    entity_id:str; center:Point2D; radius:float; source:str='VISION_DETECTED'; confidence:float|None=None
    @property
    def kind(self)->PrimitiveKind:return 'CIRCLE'
    def __post_init__(self):
        if self.radius<=0: raise ValueError('circle radius must be positive')
    def to_dict(self):return {'entity_id':self.entity_id,'kind':self.kind,'center':self.center.to_dict(),'radius':float(self.radius),'source':self.source,'confidence':self.confidence}
@dataclass(frozen=True)
class Arc:
    entity_id:str; center:Point2D; radius:float; start_angle_deg:float; end_angle_deg:float; source:str='VISION_DETECTED'; confidence:float|None=None
    @property
    def kind(self)->PrimitiveKind:return 'ARC'
    def __post_init__(self):
        if self.radius<=0: raise ValueError('arc radius must be positive')
    def to_dict(self):return {'entity_id':self.entity_id,'kind':self.kind,'center':self.center.to_dict(),'radius':float(self.radius),'start_angle_deg':float(self.start_angle_deg),'end_angle_deg':float(self.end_angle_deg),'source':self.source,'confidence':self.confidence}
GeometryPrimitive=Union[Line,Circle,Arc]
@dataclass(frozen=True)
class MeasurementRef:
    measurement_id:str; measurement_type:str; value:float; unit:str; verified:bool; source:str; target_entity_ids:tuple[str,...]; vision_estimate:float|None=None
    def __post_init__(self):
        if not self.measurement_id: raise ValueError('measurement_id is required')
        if not self.target_entity_ids: raise ValueError('target_entity_ids must not be empty')
@dataclass(frozen=True)
class ConstraintCandidate:
    constraint_id:str; kind:ConstraintKind; entity_ids:tuple[str,...]; inferred:bool=True; confidence:float=1.0
    def to_dict(self):return {'constraint_id':self.constraint_id,'kind':self.kind,'entity_ids':list(self.entity_ids),'inferred':self.inferred,'confidence':float(self.confidence)}
@dataclass(frozen=True)
class DimensionBinding:
    dimension_id:str; measurement_id:str; value:float; unit:str; verified:bool; source:str; target_entity_ids:tuple[str,...]
    def to_dict(self):return {'dimension_id':self.dimension_id,'measurement_id':self.measurement_id,'value':float(self.value),'unit':self.unit,'verified':self.verified,'source':self.source,'target_entity_ids':list(self.target_entity_ids)}
@dataclass(frozen=True)
class GeometryConflict:
    conflict_id:str; code:str; measurement_id:str; measured_value:float; derived_value:float; delta:float; tolerance:float
    def to_dict(self):return {'conflict_id':self.conflict_id,'code':self.code,'measurement_id':self.measurement_id,'measured_value':float(self.measured_value),'derived_value':float(self.derived_value),'delta':float(self.delta),'tolerance':float(self.tolerance)}
@dataclass(frozen=True)
class GeometryDraft:
    graph: object
    entities:tuple[GeometryPrimitive,...]=field(default_factory=tuple); constraints:tuple[ConstraintCandidate,...]=field(default_factory=tuple); dimensions:tuple[DimensionBinding,...]=field(default_factory=tuple); conflicts:tuple[GeometryConflict,...]=field(default_factory=tuple)
    def to_dict(self):return {'internal_format':'MREA_CHAT3_GEOMETRY_DRAFT_V1','graph':self.graph.to_dict(),'entities':[e.to_dict() for e in self.entities],'constraints':[c.to_dict() for c in self.constraints],'dimensions':[d.to_dict() for d in self.dimensions],'conflicts':[c.to_dict() for c in self.conflicts]}
