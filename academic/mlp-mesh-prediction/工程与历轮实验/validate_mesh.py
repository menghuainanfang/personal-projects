"""Geometric acceptance checks for the fixed square triangulation."""
import numpy as np
from src.geometry import signed_triangle_areas

def mesh_status(nodes,reference,cells,boundary,epsilon):
    nodes=np.asarray(nodes)
    finite=nodes.shape==reference.shape and bool(np.all(np.isfinite(nodes)))
    if not finite:
        return dict(valid=False,finite=False,boundary_fixed=False,in_domain=False,
                    min_area=None,flipped_cells=None,area_sum=None)
    areas=signed_triangle_areas(nodes,cells)
    fixed=bool(np.array_equal(nodes[boundary],reference[boundary]))
    inside=bool(np.all((nodes>=0)&(nodes<=1)))
    return dict(valid=bool(fixed and inside and areas.min()>epsilon),finite=True,
                boundary_fixed=fixed,in_domain=inside,min_area=float(areas.min()),
                flipped_cells=int(np.sum(areas<=0)),area_sum=float(areas.sum()))
