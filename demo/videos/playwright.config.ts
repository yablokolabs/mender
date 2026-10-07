import { defineConfig } from "@playwright/test";

const port = 5179;

export default defineConfig({
	testDir: "./tests",
	reporter: "list",
	use: {
		baseURL: `http://localhost:${port}`,
		viewport: { width: 1920, height: 1080 },
	},
	webServer: {
		command: `npx videowright dev --port ${port}`,
		url: `http://localhost:${port}`,
		reuseExistingServer: true,
	},
});
