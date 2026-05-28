/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MAP_INDEX_URL?: string;
  readonly VITE_IMAGE_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
