import { mkdir, writeFile } from "node:fs/promises";

const out = new URL("../web/assets/memodot/", import.meta.url);
await mkdir(out, { recursive: true });
const specs = [
  ["00-M-a", "M", `<path d="M32 160V38h26l42 67 42-67h26v122h-30V88l-38 58h-1L61 88v72z" fill="#1e3a46"/><circle cx="42" cy="29" r="10" fill="#ef815f"/>`],
  ["00-M-b", "M", `<path d="M30 154V48q0-14 14-14h28l28 44 28-44h28q14 0 14 14v106h-31V78l-37 56-37-56v76z" fill="#e6b84f"/><path d="M35 165h120" stroke="#d95d46" stroke-width="9" stroke-linecap="round"/>`],
  ["01-e-a", "e", `<path d="M36 108c0-40 27-65 62-65 37 0 57 25 57 69H68c3 18 15 27 34 27 13 0 25-4 38-13l13 23c-15 13-34 19-55 19-38 0-62-22-62-60zm32-18h56c-3-15-12-23-28-23-15 0-24 8-28 23z" fill="#c65c7b"/><circle cx="134" cy="40" r="11" fill="#7db7a5"/>`],
  ["01-e-b", "e", `<path d="M40 111q0-68 64-68 58 0 58 64v10H72q4 24 32 24 22 0 38-13l16 22q-22 22-58 22-60 0-60-61zm33-17h57q-4-23-29-23-22 0-28 23z" fill="#77a9d4"/><path d="M53 151q25 12 49 12" stroke="#f5dfab" stroke-width="8" fill="none"/>`],
  ["02-m-a", "m", `<path d="M28 160V48h29v15q17-20 39-20 22 0 32 20 19-20 42-20 37 0 37 45v72h-31V95q0-23-17-23-16 0-25 18v70h-31V95q0-23-17-23-17 0-27 19v69z" fill="#805d9b"/><path d="M39 38l111-20" stroke="#e8a24f" stroke-width="7"/>`],
  ["02-m-b", "m", `<path d="M31 157V55h28v14q18-20 40-20 24 0 34 21 17-21 40-21 37 0 37 48v60h-31v-57q0-25-17-25-16 0-26 19v63h-30v-60q0-22-17-22-18 0-28 20v62z" fill="#ed765d"/><circle cx="57" cy="42" r="9" fill="#2a6c62"/><circle cx="173" cy="38" r="8" fill="#2a6c62"/>`],
  ["03-o-a", "o", `<ellipse cx="100" cy="101" rx="66" ry="70" fill="#2f776f"/><ellipse cx="100" cy="101" rx="28" ry="34" fill="#f4f0e8"/><path d="M34 92q65-31 132 0" stroke="#f0b84f" stroke-width="10" fill="none"/><circle cx="156" cy="45" r="10" fill="#d95d46"/>`],
  ["03-o-b", "o", `<path d="M100 29c44 0 70 28 70 72s-26 72-70 72-70-28-70-72 26-72 70-72z" fill="#df8064"/><path d="M100 67c-19 0-31 12-31 34s12 34 31 34 31-12 31-34-12-34-31-34z" fill="#f4f0e8"/><path d="M40 44l120 114" stroke="#315866" stroke-width="7"/>`],
  ["04-D-a", "D", `<path d="M34 34h58c45 0 73 27 73 67s-28 67-73 67H34zm35 30v74h21c25 0 39-13 39-37S115 64 90 64z" fill="#f0bb4e"/><path d="M34 34h20v134H34z" fill="#3d6d71"/><circle cx="160" cy="38" r="9" fill="#d95d46"/>`],
  ["04-D-b", "D", `<path d="M39 39h51c48 0 78 25 78 62s-30 62-78 62H39zm35 30v64h15c27 0 43-12 43-32s-16-32-43-32z" fill="#b86c91"/><path d="M39 39l129 124" stroke="#77a9d4" stroke-width="9"/><circle cx="51" cy="30" r="10" fill="#e6b84f"/>`],
  ["05-o-a", "o", `<path d="M100 31c42 0 68 29 68 70s-26 70-68 70-68-29-68-70 26-70 68-70z" fill="#1e3a46"/><ellipse cx="100" cy="101" rx="28" ry="36" fill="#ef815f"/><path d="M42 160l116-118" stroke="#e6b84f" stroke-width="8"/><circle cx="47" cy="43" r="9" fill="#7db7a5"/>`],
  ["05-o-b", "o", `<ellipse cx="100" cy="101" rx="70" ry="68" fill="#7db7a5"/><ellipse cx="100" cy="101" rx="34" ry="40" fill="#f4f0e8"/><path d="M47 48q54 17 106 0" stroke="#805d9b" stroke-width="10" fill="none"/><path d="M47 154q54-17 106 0" stroke="#ef815f" stroke-width="10" fill="none"/>`],
  ["06-t-a", "t", `<path d="M84 39V18h33v21h31v28h-31v48q0 15 13 15 9 0 18-5l8 28q-15 9-34 9-38 0-38-43V67H62V39z" fill="#d95d46"/><path d="M62 39h86" stroke="#2f776f" stroke-width="8"/><circle cx="132" cy="22" r="10" fill="#f0bb4e"/>`],
  ["06-t-b", "t", `<path d="M78 43V21h35v22h35v27h-35v43q0 17 15 17 10 0 19-6l8 28q-16 10-38 10-39 0-39-46V70H56V43z" fill="#805d9b"/><path d="M59 160l104-117" stroke="#ef815f" stroke-width="8"/><circle cx="72" cy="25" r="9" fill="#77a9d4"/>`]
];
for (const [name, char, art] of specs) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img" aria-label="${char}"><title>${char}</title><g stroke-linejoin="round" stroke-linecap="round">${art}</g></svg>`;
  await writeFile(new URL(`${name}.svg`, out), svg);
}
