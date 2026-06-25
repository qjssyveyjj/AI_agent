import { useEffect, useState } from "react";

interface Stats {
  conversations: number;
  messages: number;
  toolCalls: number;
}

const THROUGHPUT_BARS = [62, 78, 55, 90, 73, 84, 68, 95, 80, 71, 88, 76];

export default function Dashboard({ stats }: { stats: Stats }) {
  // 模拟实时生产指标的轻微波动
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((v) => v + 1), 2000);
    return () => clearInterval(t);
  }, []);

  const wobble = (base: number, amp: number) =>
    (base + Math.sin(tick / 2) * amp).toFixed(1);

  const onlineRate = 98.6;

  return (
    <aside className="dashboard">
      <div className="dash-head">
        <span className="dash-title">生产数据大屏</span>
        <span className="live">
          <span className="live-dot" /> 实时
        </span>
      </div>

      <div className="kpi-grid">
        <Kpi label="今日吞吐量(吨)" value={wobble(48200, 60)} accent="cyan" />
        <Kpi label="在港船舶(艘)" value="17" accent="blue" />
        <Kpi label="作业效率(%)" value={wobble(92.4, 1.2)} accent="violet" />
        <Kpi label="待处理工单" value="23" accent="amber" />
      </div>

      <div className="panel">
        <div className="panel-title">设备在线率</div>
        <Ring percent={onlineRate} />
      </div>

      <div className="panel">
        <div className="panel-title">近 12 小时吞吐趋势</div>
        <div className="bars">
          {THROUGHPUT_BARS.map((h, i) => (
            <div className="bar" key={i} style={{ height: `${h}%` }} />
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">AI 助手运行状态</div>
        <div className="ai-stats">
          <StatRow label="累计会话" value={stats.conversations} />
          <StatRow label="消息总数" value={stats.messages} />
          <StatRow label="工具调用" value={stats.toolCalls} />
          <StatRow label="模型" value="Qwen3-VL" mono />
        </div>
      </div>

      <div className="panel alarms">
        <div className="panel-title">告警动态</div>
        <ul>
          <li className="ok">3号泊位作业正常</li>
          <li className="warn">2号皮带机温度偏高</li>
          <li className="ok">门机群通讯正常</li>
        </ul>
      </div>
    </aside>
  );
}

function Kpi({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className={`kpi ${accent}`}>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}

function StatRow({ label, value, mono }: { label: string; value: number | string; mono?: boolean }) {
  return (
    <div className="stat-row">
      <span>{label}</span>
      <span className={mono ? "mono" : "num"}>{value}</span>
    </div>
  );
}

function Ring({ percent }: { percent: number }) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - percent / 100);
  return (
    <div className="ring">
      <svg viewBox="0 0 100 100">
        <circle className="ring-bg" cx="50" cy="50" r={r} />
        <circle
          className="ring-fg"
          cx="50"
          cy="50"
          r={r}
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="ring-label">
        <strong>{percent}%</strong>
        <span>在线</span>
      </div>
    </div>
  );
}
