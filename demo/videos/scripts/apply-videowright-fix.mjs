// videowright 0.1.1 publishes src/cli/entry, but not the two modules that those entry
// files import. From a clean install, `videowright render` and the dev video page
// stop with: Failed to resolve import "../../index.js".
// This writes the missing modules as re-exports of the compiled code in dist/.
// A file that a later videowright version ships is left as it is.
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const packageSrc = join(projectRoot, "node_modules", "videowright", "src");
const missingModules = {
	"index.js": 'export * from "../dist/index.js";\n',
	"timeline/resolveTiming.js": 'export * from "../../dist/timeline/resolveTiming.js";\n',
};

for (const [file, content] of Object.entries(missingModules)) {
	const target = join(packageSrc, file);
	if (existsSync(target)) continue;
	mkdirSync(dirname(target), { recursive: true });
	writeFileSync(target, content);
}
