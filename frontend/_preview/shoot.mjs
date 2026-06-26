import { chromium } from "playwright";
import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const URL = "http://localhost:5173/";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await page.goto(URL, { waitUntil: "networkidle" });

// 1. 初始空状态
await page.waitForSelector(".composer-row");
await page.screenshot({ path: path.join(__dirname, "01-empty.png") });

// 2. 点击 "+" 打开菜单
await page.click(".attach-btn");
await page.waitForSelector(".attach-menu");
await page.screenshot({ path: path.join(__dirname, "02-menu.png") });

// 3. 通过隐藏 input 选择文件（图片 + 文档），并输入文字
await page.setInputFiles('input[accept*=".pdf"]', [
  path.join(__dirname, "report.pdf"),
  path.join(__dirname, "生产数据.xlsx"),
]);
await page.fill("textarea", "帮我分析这两个附件里的生产数据");
await page.waitForSelector(".doc-chip");
await page.screenshot({ path: path.join(__dirname, "03-attachments.png") });

// 4. 发送后展示用户气泡（后端未启动会触发 error 事件，顺带演示错误提示）
await page.click(".send-btn");
await page.waitForTimeout(2500);
await page.screenshot({ path: path.join(__dirname, "04-sent.png") });

await browser.close();
console.log("SHOTS_DONE");
