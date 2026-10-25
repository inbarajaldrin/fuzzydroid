# Analytic FK/IK for Universal Robots arms (UR3e/UR5e/UR10e/UR16e).
#
# Standard DH convention, parameters from ur_description default_kinematics.
# Frames: "dh_base" (frame 0) and "dh_flange" (frame 6). These differ from
# ur_description's base_link/tool0 by fixed Rz(pi) offsets on both ends; the
# jog server exposes poses in the dh frames and documents the convention.
#
# Reference: https://github.com/UniversalRobots/Universal_Robots_ROS2_Description
# Closed-form solution follows the classic UR derivation (wrist-center theta1,
# decoupled theta5/theta6, planar 2R for theta2/theta3/theta4).

import math

# d1, a2, a3, d4, d5, d6  (meters)
UR_PARAMS = {
    'ur3e':  dict(d1=0.15185, a2=-0.24355, a3=-0.2132,  d4=0.13105, d5=0.08535, d6=0.0921),
    'ur5e':  dict(d1=0.1625,  a2=-0.425,   a3=-0.3922,  d4=0.1333,  d5=0.0997,  d6=0.0996),
    'ur10e': dict(d1=0.1807,  a2=-0.6127,  a3=-0.57155, d4=0.17415, d5=0.11985, d6=0.11655),
    'ur16e': dict(d1=0.1807,  a2=-0.4784,  a3=-0.36,    d4=0.17415, d5=0.11985, d6=0.11655),
}

_ALPHA = (math.pi / 2, 0.0, 0.0, math.pi / 2, -math.pi / 2, 0.0)


def _dh(theta, d, a, alpha):
    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return [
        [ct, -st * ca,  st * sa, a * ct],
        [st,  ct * ca, -ct * sa, a * st],
        [0.0,      sa,       ca,      d],
        [0.0,     0.0,      0.0,    1.0],
    ]


def _matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def fk(q, variant='ur5e'):
    """Pose of dh_flange in dh_base for joint vector q (radians). Returns 4x4."""
    p = UR_PARAMS[variant]
    d = (p['d1'], 0.0, 0.0, p['d4'], p['d5'], p['d6'])
    a = (0.0, p['a2'], p['a3'], 0.0, 0.0, 0.0)
    T = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    for i in range(6):
        T = _matmul(T, _dh(q[i], d[i], a[i], _ALPHA[i]))
    return T


def rpy_to_matrix(roll, pitch, yaw):
    """URDF-convention fixed-axis XYZ rpy → 3x3 rotation (as rows of a 4x4-ready list)."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp,     cp * sr,                cp * cr],
    ]


def matrix_to_rpy(R):
    """3x3 (or 4x4) rotation → URDF fixed-axis XYZ rpy."""
    sp = -R[2][0]
    sp = max(-1.0, min(1.0, sp))
    pitch = math.asin(sp)
    if abs(sp) > 0.999999:
        # Gimbal lock: fold yaw into roll
        roll = math.atan2(-R[0][1], R[1][1])
        yaw = 0.0
    else:
        roll = math.atan2(R[2][1], R[2][2])
        yaw = math.atan2(R[1][0], R[0][0])
    return roll, pitch, yaw


def pose_matrix(xyz, rpy):
    R = rpy_to_matrix(*rpy)
    return [
        [R[0][0], R[0][1], R[0][2], xyz[0]],
        [R[1][0], R[1][1], R[1][2], xyz[1]],
        [R[2][0], R[2][1], R[2][2], xyz[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def ik(T, variant='ur5e'):
    """All closed-form solutions (up to 8) for dh_flange pose T (4x4) in dh_base.

    Returns a list of 6-vectors (radians, each wrapped to [-pi, pi]).
    """
    p = UR_PARAMS[variant]
    d1, a2, a3, d4, d5, d6 = p['d1'], p['a2'], p['a3'], p['d4'], p['d5'], p['d6']

    nx, ox, ax, px = T[0][0], T[0][1], T[0][2], T[0][3]
    ny, oy, ay, py = T[1][0], T[1][1], T[1][2], T[1][3]
    nz, oz, az, pz = T[2][0], T[2][1], T[2][2], T[2][3]

    sols = []

    # theta1 — from wrist center (frame-5 origin projected to base plane)
    p5x = px - d6 * ax
    p5y = py - d6 * ay
    r = math.hypot(p5x, p5y)
    if r < 1e-12 or abs(d4) > r:
        return []
    phi = math.atan2(p5y, p5x)
    alpha = math.acos(max(-1.0, min(1.0, d4 / r)))
    for t1 in (phi + alpha + math.pi / 2, phi - alpha + math.pi / 2):
        t1 = _wrap(t1)
        s1, c1 = math.sin(t1), math.cos(t1)

        # theta5 — from the flange x-y plane offset along joint-1 axis
        c5 = s1 * ax - c1 * ay
        num = px * s1 - py * c1 - d4
        arg = max(-1.0, min(1.0, num / d6))
        for t5 in (math.acos(arg), -math.acos(arg)):
            s5 = math.sin(t5)

            # theta6 — undefined when s5 ~ 0 (wrist singularity): pick 0
            if abs(s5) < 1e-8:
                t6 = 0.0
            else:
                t6 = math.atan2((-s1 * ox + c1 * oy) / s5, (s1 * nx - c1 * ny) / s5)
            t6 = _wrap(t6)

            # Decouple: T14 = inv(T01) * T * inv(T45*T56) → planar 2R chain
            # Compute frame-4 origin and x-axis in the frame after joint 1.
            T01 = _dh(t1, d1, 0.0, _ALPHA[0])
            T45 = _dh(t5, d5, 0.0, _ALPHA[4])
            T56 = _dh(t6, d6, 0.0, _ALPHA[5])
            T46 = _matmul(T45, T56)
            T14 = _matmul(_inv(T01), _matmul(T, _inv(T46)))

            # Joints 2-3 rotate about frame-1 z: the elbow plane is frame-1 x-y,
            # with the frame-4 origin's z pinned at d4.
            x14, y14 = T14[0][3], T14[1][3]
            L = math.hypot(x14, y14)
            if L > abs(a2) + abs(a3) + 1e-9 or L < abs(abs(a2) - abs(a3)) - 1e-9:
                continue
            c3 = (L * L - a2 * a2 - a3 * a3) / (2 * a2 * a3)
            c3 = max(-1.0, min(1.0, c3))
            for t3 in (math.acos(c3), -math.acos(c3)):
                s3 = math.sin(t3)
                t2 = math.atan2(y14, x14) - math.atan2(a3 * s3, a2 + a3 * math.cos(t3))
                t2 = _wrap(t2)
                # theta4 from the remaining orientation about the planar axis
                T12 = _dh(t2, 0.0, a2, _ALPHA[1])
                T23 = _dh(t3, 0.0, a3, _ALPHA[2])
                T34 = _matmul(_inv(T23), _matmul(_inv(T12), T14))
                t4 = _wrap(math.atan2(T34[1][0], T34[0][0]))
                q = [t1, t2, _wrap(t3), t4, _wrap(t5), t6]
                if _fk_matches(q, T, variant):
                    sols.append(q)
    return sols


def _inv(T):
    """Invert a rigid transform."""
    R = [[T[j][i] for j in range(3)] for i in range(3)]  # transpose
    t = [T[0][3], T[1][3], T[2][3]]
    ti = [-(R[i][0] * t[0] + R[i][1] * t[1] + R[i][2] * t[2]) for i in range(3)]
    return [
        [R[0][0], R[0][1], R[0][2], ti[0]],
        [R[1][0], R[1][1], R[1][2], ti[1]],
        [R[2][0], R[2][1], R[2][2], ti[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _fk_matches(q, T, variant, tol=1e-6):
    F = fk(q, variant)
    return all(abs(F[i][j] - T[i][j]) < tol for i in range(3) for j in range(4))


def select_nearest(solutions, current):
    """Pick the solution closest (sum of wrapped joint deltas) to `current`."""
    best, best_cost = None, None
    for q in solutions:
        cost = sum(abs(_wrap(q[i] - current[i])) for i in range(6))
        if best_cost is None or cost < best_cost:
            best, best_cost = q, cost
    return best


if __name__ == '__main__':
    # Round-trip self-test: FK(q) → IK → one solution must reproduce q.
    import random
    random.seed(7)
    fails = 0
    for variant in UR_PARAMS:
        for _ in range(200):
            q = [random.uniform(-math.pi, math.pi) for _ in range(6)]
            T = fk(q, variant)
            sols = ik(T, variant)
            ok = any(all(abs(_wrap(s[i] - q[i])) < 1e-5 for i in range(6)) for s in sols)
            if not ok:
                fails += 1
                print(f'FAIL {variant}: q={[round(v,3) for v in q]} ({len(sols)} sols)')
    print(f'self-test: {"OK" if fails == 0 else f"{fails} FAILURES"} '
          f'({len(UR_PARAMS)} variants x 200 random poses)')
