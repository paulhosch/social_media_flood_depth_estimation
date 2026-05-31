import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

import { cloudflare } from "@cloudflare/vite-plugin";

const repoRoot = path.resolve(fileURLToPath(new URL("../..", import.meta.url)));
const imagesDir = path.join(repoRoot, "data", "exif_images", "images");

function attachImageMiddleware(
  middlewares: { use: (path: string, handler: (...args: unknown[]) => void) => void },
): void {
  middlewares.use("/dataset/images", (req, res, next) => {
    const reqUrl = (req as { url?: string }).url ?? "";
    const resObj = res as {
      setHeader: (k: string, v: string) => void;
      statusCode?: number;
      end: (s?: string) => void;
    };
    const nextFn = next as () => void;
    const name = path.basename(decodeURIComponent(reqUrl));
    if (!name || name === "." || name.includes("..")) {
      nextFn();
      return;
    }
    const filePath = path.join(imagesDir, name);
    if (!filePath.startsWith(imagesDir) || !fs.existsSync(filePath)) {
      nextFn();
      return;
    }
    resObj.setHeader("Content-Type", "image/jpeg");
    fs.createReadStream(filePath).pipe(res as NodeJS.WritableStream);
  });
}

function serveDatasetImages(): Plugin {
  return {
    name: "serve-dataset-images",
    configureServer(server) {
      attachImageMiddleware(server.middlewares);
    },
    configurePreviewServer(server) {
      attachImageMiddleware(server.middlewares);
    },
  };
}

export default defineConfig({
  plugins: [react(), serveDatasetImages(), cloudflare()],
  server: {
    host: true,
    port: 5173,
    fs: {
      allow: [repoRoot],
    },
  },
  resolve: {
    alias: {
      "mapbox-gl": "maplibre-gl",
    },
  },
});