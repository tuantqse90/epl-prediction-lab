// Minimal TS port of backend `app/models/poisson.py`, used to re-derive the
// scoreline probability matrix from published lambdas for the heatmap UI. The
// result is for display only — on-chain-style verification still uses the
// backend commitment hash.

export function poissonPMF(k: number, lambda: number): number {
  if (lambda <= 0) return k === 0 ? 1 : 0;
  let p = Math.exp(-lambda);
  for (let i = 1; i <= k; i++) p *= lambda / i;
  return p;
}

export function scoreMatrix(
  lamH: number,
  lamA: number,
  rho: number,
  maxGoals = 5,
): number[][] {
  const n = maxGoals + 1;
  const m: number[][] = Array.from({ length: n }, () => Array(n).fill(0));

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      m[i][j] = poissonPMF(i, lamH) * poissonPMF(j, lamA);
    }
  }

  // Dixon-Coles correction on the four low-scoring cells
  m[0][0] *= 1 - lamH * lamA * rho;
  m[0][1] *= 1 + lamH * rho;
  m[1][0] *= 1 + lamA * rho;
  m[1][1] *= 1 - rho;

  return m;
}

export function modelVersionToRho(modelVersion: string | null | undefined, fallback = -0.15): number {
  if (!modelVersion) return fallback;
  const m = modelVersion.match(/rho=(-?\d+(?:\.\d+)?)/);
  return m ? Number(m[1]) : fallback;
}
