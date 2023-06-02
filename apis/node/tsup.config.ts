import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts", "src/fs.ts"],
  splitting: false,
  sourcemap: false,
  dts: true,
  clean: true,
});
