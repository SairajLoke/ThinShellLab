"""Crease test: the Folding scene plus a press plate, for scripted (not optimised) press-and-open experiments.

Same paper strip, table box and fingertip as Scene_folding (fingertip starting away from the paper), plus a third body: a frozen\nbox ("plate") that is moved by script.
Contact between the plate and the sheet comes from the inherited contact_analysis, which loops over all elastics.
Used by tools/crease_test.py.
"""
import os
import taichi as ti
import numpy as np

from .Scene_folding import Scene as FoldingScene
from ..engine.model_fold_offset import Cloth
from ..engine.model_elastic_offset import Elastic
from ..engine.model_elastic_tactile import Elastic as tactile


@ti.data_oriented
class Scene(FoldingScene):

    def init_scene_parameters(self):
        super(Scene, self).init_scene_parameters()
        self.elastic_cnt = 3        # table box, fingertip, plate
        self.k_contact = float(os.environ.get("CT_K", self.k_contact))   # contact stiffness (Folding: 1e4)
        self.effector_cnt = 2       # the gripper drives only the fingertip
        self.plate_size = 0.06      # 60 x 60 x 10 mm (7 x 7 x 2 nodes): covers the whole folded strip
        self.plate_origin = (-0.026, -0.03, 0.05)   # min corner
        self.finger_start = (0.05, 0.035)           # x, z of the fingertip centre: clear of the paper and the plate

    def init_objects(self):
        rho = 4e1
        self.cloths.append(Cloth(self.cloth_N, self.dt, self.cloth_size, self.tot_NV, rho, 0, False, 3))
        tmp_tot = (self.cloth_N + 1) * (self.cloth_M + 1)
        self.elastics.append(Elastic(self.dt, self.elastic_size[0], tmp_tot, self.elastic_Nx, self.elastic_Ny, self.elastic_Nz))
        tmp_tot += self.elastic_Nx * self.elastic_Ny * self.elastic_Nz
        self.elastics.append(tactile(self.dt, tmp_tot, self.elastic_size[1] / 0.03))
        tmp_tot += self.elastics[1].n_verts
        self.elastics.append(Elastic(self.dt, self.plate_size, tmp_tot, 7, 7, 2))
        tmp_tot += self.elastics[2].n_verts
        self.tot_NV = tmp_tot

    def init(self):
        # as Scene_folding.init, but the fingertip starts away from the paper (in Folding it starts pressed onto the fold)
        half_curve_num = 2
        self.cloths[0].init_fold(-0.07, -0.01, 0.0004, half_curve_num)
        self.elastics[0].init(-0.035, -0.035, -0.00875)
        x, z = self.finger_start
        self.elastics[1].init(x, 0.0, z, True)
        self.gripper.init(self, np.array([[x, 0.0, z]]))
        self.elastics[2].init(*self.plate_origin)

    def reset_pos(self):
        self.init()

    def set_frozen(self):
        super(Scene, self).set_frozen()
        self.freeze_body(self.elastics[2].offset, self.elastics[2].n_verts, 1)

    @ti.kernel
    def freeze_body(self, start: ti.i32, n: ti.i32, value: ti.i32):
        for i in range(start, start + n):
            for d in ti.static(range(3)):
                self.frozen[i * 3 + d] = value

    # ---- scripted motion of frozen vertices (call push_down_pos() afterwards)
    @ti.kernel
    def translate_vertices(self, start: ti.i32, n: ti.i32, dx: ti.f64, dy: ti.f64, dz: ti.f64):
        for i in range(start, start + n):
            self.pos[i] += ti.Vector([dx, dy, dz])

    @ti.kernel
    def set_vertex(self, i: ti.i32, x: ti.f64, y: ti.f64, z: ti.f64):
        self.pos[i] = ti.Vector([x, y, z])

    def move_plate(self, dx, dy, dz):
        self.translate_vertices(self.elastics[2].offset, self.elastics[2].n_verts, dx, dy, dz)
        self.push_down_pos()

    @ti.kernel
    def damp_cloth_velocity(self, factor: ti.f64):
        for i in range(self.cloths[0].NV):
            self.vel[i] *= factor

    def damp_sheet(self, factor):
        """Scripted velocity damping of the sheet (the scene has no gravity and no air drag, so a released flap would swing forever)."""
        self.damp_cloth_velocity(factor)
        self.push_down_vel()

    # ---- measurements
    @ti.kernel
    def hinge_data(self, out: ti.types.ndarray()):
        """One row per interior edge: hinge position (in grid rows), plastic rest angle, current angle, valid flag."""
        for i in range(self.cloths[0].NF):
            for l in range(3):
                j = self.cloths[0].counter_face[i][l]
                k = i * 3 + l
                out[k, 3] = 0.0
                if j > i:
                    p1 = self.cloths[0].f2v[i][l]
                    p2 = self.cloths[0].f2v[j][self.cloths[0].counter_point[i][l]]
                    out[k, 0] = (p1 // (self.cloths[0].M + 1) + p2 // (self.cloths[0].M + 1)) / 2.0
                    out[k, 1] = self.cloths[0].ref_angle[i][l]
                    out[k, 2] = self.cloths[0].compute_angle(i, j, l)
                    out[k, 3] = 1.0
