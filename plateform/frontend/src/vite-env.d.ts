/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_MAP_TILE_URL?: string;
  readonly VITE_MAP_ATTRIBUTION?: string;
  readonly VITE_TESTBED_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
