"use client";

/**
 * The hero's 3D paper plane: a real folded dart (wings + keel), ruled like a
 * notebook page, drifting on its own, banking toward the pointer and rolling
 * as the visitor scrolls. Loaded lazily; the SVG mark stands in until then.
 */
import { Canvas, useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import { useMemo, useRef } from "react";
import * as THREE from "three";

function ruledTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const g = c.getContext("2d")!;
  g.fillStyle = "#fffdf7";
  g.fillRect(0, 0, 512, 512);
  g.strokeStyle = "#c9d8ee";
  g.lineWidth = 3;
  for (let y = 40; y < 512; y += 38) { g.beginPath(); g.moveTo(0, y); g.lineTo(512, y); g.stroke(); }
  g.strokeStyle = "#e5917f";
  g.lineWidth = 3;
  g.beginPath(); g.moveTo(90, 0); g.lineTo(90, 512); g.stroke();
  // the ॥ pause mark on the wing
  g.strokeStyle = "#3b66ae";
  g.lineWidth = 14;
  g.lineCap = "round";
  for (const x of [270, 320]) { g.beginPath(); g.moveTo(x + 12, 190); g.lineTo(x - 6, 300); g.stroke(); }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

function usePlaneGeometry() {
  return useMemo(() => {
    // nose, wing tips, tail centre, keel bottom
    const N = [0, 0.05, 1.9], L = [-1.25, 0.12, -1.05], R = [1.25, 0.12, -1.05], T = [0, 0, -1.05], K = [0, -0.42, -1.05];
    const tris = [N, T, L, N, R, T, N, K, T, N, T, K];
    const uvs = [0.5, 1, 0.5, 0, 0, 0, 0.5, 1, 1, 0, 0.5, 0, 0.5, 1, 0.3, 0, 0.5, 0, 0.5, 1, 0.5, 0, 0.7, 0];
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(tris.flat(), 3));
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    geo.computeVertexNormals();
    return geo;
  }, []);
}

function Plane({ scrollRef }: { scrollRef: React.RefObject<number> }) {
  const group = useRef<THREE.Group>(null);
  const geo = usePlaneGeometry();
  const tex = useMemo(() => ruledTexture(), []);
  const edges = useMemo(() => new THREE.EdgesGeometry(geo, 1), [geo]);

  useFrame((state, dt) => {
    const g = group.current;
    if (!g) return;
    const { x, y } = state.pointer;
    const s = scrollRef.current ?? 0;
    g.rotation.y = THREE.MathUtils.damp(g.rotation.y, -0.6 + x * 0.5 + s * 2.2, 3, dt);
    g.rotation.x = THREE.MathUtils.damp(g.rotation.x, 0.35 - y * 0.3, 3, dt);
    g.rotation.z = THREE.MathUtils.damp(g.rotation.z, -x * 0.45 + Math.sin(state.clock.elapsedTime * 0.8) * 0.06, 3, dt);
    g.position.x = THREE.MathUtils.damp(g.position.x, x * 0.35 + s * 2.5, 2.5, dt);
    g.position.y = THREE.MathUtils.damp(g.position.y, y * 0.2 + s * 1.4, 2.5, dt);
  });

  return (
    <Float speed={1.6} rotationIntensity={0.25} floatIntensity={0.9}>
      <group ref={group} scale={0.82}>
        <mesh geometry={geo} castShadow>
          <meshStandardMaterial map={tex} side={THREE.DoubleSide} roughness={0.92} metalness={0} flatShading />
        </mesh>
        <lineSegments geometry={edges}>
          <lineBasicMaterial color="#1e2942" transparent opacity={0.55} />
        </lineSegments>
      </group>
    </Float>
  );
}

export default function Plane3D({ scrollRef }: { scrollRef: React.RefObject<number> }) {
  return (
    <Canvas dpr={[1, 2]} camera={{ position: [0, 0.6, 5.2], fov: 38 }} gl={{ antialias: true, alpha: true }} style={{ pointerEvents: "none" }} eventSource={typeof document !== "undefined" ? document.body : undefined} eventPrefix="client">
      <ambientLight intensity={1.15} />
      <directionalLight position={[3, 5, 4]} intensity={1.4} color="#fff6e5" />
      <directionalLight position={[-4, -2, -3]} intensity={0.45} color="#c3d7f2" />
      <Plane scrollRef={scrollRef} />
    </Canvas>
  );
}
