"""Physical mesh metrics and fixed-point interpolation of an analytic field."""
import numpy as np
from matplotlib.tri import Triangulation,LinearTriInterpolator
from common import signed_triangle_areas

def sample_points(n=160):
    t=(np.arange(n)+.5)/n;x,y=np.meshgrid(t,t)
    return np.column_stack((x.ravel(),y.ravel()))

def field(x,mu):
    return np.exp(-((x-np.asarray(mu[:2]))**2).sum(axis=-1)/mu[3]**2)

def interpolation_rmse(x,cells,mu,points):
    tri=Triangulation(x[:,0],x[:,1],cells)
    values=LinearTriInterpolator(tri,field(x,mu))(points[:,0],points[:,1])
    if np.any(np.ma.getmaskarray(values)):raise ValueError('Sampling points outside mesh')
    return float(np.sqrt(np.mean((np.asarray(values)-field(points,mu))**2)))

def geometry(x,cells):
    triangles=x[cells]
    edges=[triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,1],triangles[:,0]-triangles[:,2]]
    length=np.array([np.linalg.norm(v,axis=1) for v in edges]).T
    angles=[]
    for i in range(3):
        a,b,c=length[:,i],length[:,(i+1)%3],length[:,(i+2)%3]
        angles.append(np.degrees(np.arccos(np.clip((b*b+c*c-a*a)/(2*b*c),-1,1))))
    area=signed_triangle_areas(x,cells)
    quality=4*np.sqrt(3)*area/np.sum(length**2,axis=1)
    return dict(min_area=float(area.min()),flipped_cells=int(np.sum(area<=0)),
                min_angle=float(np.min(angles)),min_quality=float(quality.min()),mean_quality=float(quality.mean()))

def measure(problem,x,teacher,points):
    inside=~problem.boundary
    return dict(node_error=float(np.linalg.norm((x-teacher)[inside])/np.linalg.norm((teacher-problem.X0)[inside])),
                valid=problem.valid(x)['valid'],**geometry(x,problem.cells),
                interpolation_rmse=interpolation_rmse(x,problem.cells,problem.mu,points))
