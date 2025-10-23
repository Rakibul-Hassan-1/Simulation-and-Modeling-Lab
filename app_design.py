import React, { useMemo, useState } from "react";
import seedrandom from "seedrandom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Info, RotateCcw, Play } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  CartesianGrid,
  Legend,
} from "recharts";

// ==========================
// Types
// ==========================
interface SimulationInput {
  nCustomers: number;
  rnIat?: number[]; // 1..1000
  rnSt?: number[];  // 1..100
}

interface Row {
  Cust: number;
  RN_IAT: number;
  IAT: number;
  Arrival: number;
  RN_ST: number;
  ST: number;
  TSB: number;
  Wait: number;
  TSE: number;
  TimeInSystem: number;
  ServerIdle: number;
}

interface Summary {
  avgWait: number;
  maxWait: number;
  totalIdle: number;
  utilization: number; // 0..1
  horizonEnd: number;
}

// ==========================
// Mapping functions (ported from Python)
// ==========================
function interArrivalTimeFromRn(rn: number): number {
  if (rn < 1 || rn > 1000) throw new Error("IAT RN must be 1..1000");
  if (rn < 126) return 1;
  if (rn < 251) return 2;
  if (rn < 376) return 3;
  if (rn < 501) return 4;
  if (rn < 626) return 5;
  if (rn < 751) return 6;
  if (rn < 876) return 7;
  return 8; // rn <= 1000
}

function serviceTimeFromRn(rn: number): number {
  if (rn < 1 || rn > 100) throw new Error("ST RN must be 1..100");
  if (rn < 30) return 1;
  if (rn < 50) return 2;
  if (rn < 60) return 3;
  if (rn < 65) return 4;
  if (rn < 75) return 5;
  return 6; // rn <= 100
}

// ==========================
// Simulation core (TypeScript)
// ==========================
function simulateQueue(input: SimulationInput): { rows: Row[]; summary: Summary } {
  const n = input.nCustomers;
  if (n <= 0) throw new Error("nCustomers must be >= 1");

  const rnIat = input.rnIat ?? new Array(n).fill(0).map(() => 1 + Math.floor(Math.random() * 1000));
  const rnSt = input.rnSt ?? new Array(n).fill(0).map(() => 1 + Math.floor(Math.random() * 100));
  if (rnIat.length !== n || rnSt.length !== n) throw new Error("RN lengths must equal nCustomers");

  const iat = rnIat.map(interArrivalTimeFromRn);
  iat[0] = 0; // first arrival begins system

  const arrival: number[] = new Array(n).fill(0);
  for (let i = 1; i < n; i++) arrival[i] = arrival[i - 1] + iat[i];

  const st = rnSt.map(serviceTimeFromRn);

  const tsb: number[] = new Array(n).fill(0);
  const wt: number[] = new Array(n).fill(0);
  const tse: number[] = new Array(n).fill(0);
  const tis: number[] = new Array(n).fill(0);
  const idle: number[] = new Array(n).fill(0);

  // first customer
  tse[0] = st[0];
  tis[0] = st[0];

  for (let i = 1; i < n; i++) {
    const prevTse = tse[i - 1];
    tsb[i] = Math.max(prevTse, arrival[i]);
    wt[i] = tsb[i] - arrival[i];
    tse[i] = tsb[i] + st[i];
    tis[i] = st[i] + wt[i];
    idle[i] = Math.max(0, tsb[i] - prevTse);
  }

  const rows: Row[] = new Array(n).fill(0).map((_, i) => ({
    Cust: i + 1,
    RN_IAT: rnIat[i],
    IAT: iat[i],
    Arrival: arrival[i],
    RN_ST: rnSt[i],
    ST: st[i],
    TSB: tsb[i],
    Wait: wt[i],
    TSE: tse[i],
    TimeInSystem: tis[i],
    ServerIdle: idle[i],
  }));

  const totalService = st.reduce((a, b) => a + b, 0);
  const totalIdle = idle.reduce((a, b) => a + b, 0);
  const avgWait = wt.reduce((a, b) => a + b, 0) / n;
  const maxWait = wt.reduce((a, b) => Math.max(a, b), 0);
  const utilization = totalService + totalIdle > 0 ? totalService / (totalService + totalIdle) : 0;
  const horizonEnd = tse[n - 1];

  return {
    rows,
    summary: { avgWait, maxWait, totalIdle, utilization, horizonEnd },
  };
}

function parseCsvInts(s: string): number[] {
  return s
    .replace(/\n/g, ",")
    .split(",")
    .map((p) => p.trim())
    .filter((p) => p.length > 0)
    .map((p) => parseInt(p, 10));
}

function toFixed2(x: number) {
  return x.toFixed(2);
}


export default function App() {
  const [nCustomers, setNCustomers] = useState<number>(10);
  const [useCustomRn, setUseCustomRn] = useState(false);
  const [rnIatText, setRnIatText] = useState("");
  const [rnStText, setRnStText] = useState("");
  const [seed, setSeed] = useState<string>("");
  const [runKey, setRunKey] = useState(0);

  // Seed effect
  useMemo(() => {
    if (seed && seed.trim().length > 0) {
      seedrandom(seed, { global: true });
    }
    // No deps on seedrandom result; this runs on seed change
  }, [seed, runKey]);

  const [rows, setRows] = useState<Row[] | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = () => {
    try {
      setError(null);
      let rnIat: number[] | undefined = undefined;
      let rnSt: number[] | undefined = undefined;
      if (useCustomRn) {
        rnIat = parseCsvInts(rnIatText);
        rnSt = parseCsvInts(rnStText);
      }
      const { rows, summary } = simulateQueue({ nCustomers, rnIat, rnSt });
      setRows(rows);
      setSummary(summary);
    } catch (e: any) {
      setError(e?.message ?? String(e));
      setRows(null);
      setSummary(null);
    }
  };

  const reset = () => {
    setNCustomers(10);
    setUseCustomRn(false);
    setRnIatText("");
    setRnStText("");
    setSeed("");
    setRows(null);
    setSummary(null);
    setError(null);
    setRunKey((k) => k + 1);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl p-6 space-y-6">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Single-Server Queue Simulator</h1>
            <p className="text-sm text-slate-500 mt-1">
              Excel-like discrete event simulation with a clean UI — ported from your Python logic.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={reset}>
              <RotateCcw className="h-4 w-4 mr-2" /> Reset
            </Button>
            <Button onClick={run}>
              <Play className="h-4 w-4 mr-2" /> Run Simulation
            </Button>
          </div>
        </header>

        {/* Controls */}
        <Card className="rounded-2xl shadow-sm">
          <CardContent className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label htmlFor="n">Number of customers</Label>
                <Input
                  id="n"
                  type="number"
                  min={1}
                  value={nCustomers}
                  onChange={(e) => setNCustomers(parseInt(e.target.value || "1", 10))}
                  className="mt-2"
                />
              </div>
              <div>
                <Label htmlFor="seed">Random seed (optional)</Label>
                <Input
                  id="seed"
                  placeholder="e.g. 42"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  className="mt-2"
                />
                <p className="text-xs text-slate-500 mt-1">Use a seed for reproducible random numbers.</p>
              </div>
              <div className="flex items-end gap-3">
                <div className="space-y-1">
                  <Label>Custom RN input</Label>
                  <div className="flex items-center gap-3 mt-1">
                    <Switch checked={useCustomRn} onCheckedChange={setUseCustomRn} />
                    <span className="text-sm">Provide RN lists</span>
                  </div>
                </div>
              </div>
            </div>

            <Tabs defaultValue="random" value={useCustomRn ? "custom" : "random"}>
              <TabsList>
                <TabsTrigger value="random" onClick={() => setUseCustomRn(false)}>Random RN</TabsTrigger>
                <TabsTrigger value="custom" onClick={() => setUseCustomRn(true)}>Custom RN</TabsTrigger>
              </TabsList>
              <TabsContent value="random" className="pt-4">
                <div className="text-sm text-slate-500 flex items-center gap-2"><Info className="h-4 w-4"/> If you don’t provide RN lists, the simulator will generate them uniformly: IAT (1..1000), ST (1..100).</div>
              </TabsContent>
              <TabsContent value="custom" className="pt-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="rnIat">RN for IAT (1..1000)</Label>
                    <Textarea
                      id="rnIat"
                      placeholder="e.g. 12, 845, 310, 999, ..."
                      value={rnIatText}
                      onChange={(e) => setRnIatText(e.target.value)}
                      className="mt-2 h-28"
                    />
                  </div>
                  <div>
                    <Label htmlFor="rnSt">RN for ST (1..100)</Label>
                    <Textarea
                      id="rnSt"
                      placeholder="e.g. 5, 88, 60, 17, ..."
                      value={rnStText}
                      onChange={(e) => setRnStText(e.target.value)}
                      className="mt-2 h-28"
                    />
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-2">Comma or newline separated. Length of both lists must equal the number of customers.</p>
              </TabsContent>
            </Tabs>

            {error && (
              <div className="text-sm text-red-600">{error}</div>
            )}
          </CardContent>
        </Card>

        {/* Summary */}
        {summary && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <Kpi title="Avg wait" value={`${toFixed2(summary.avgWait)}`} suffix="" />
            <Kpi title="Max wait" value={`${summary.maxWait}`} />
            <Kpi title="Total idle" value={`${summary.totalIdle}`} />
            <Kpi title="Utilization" value={`${(summary.utilization * 100).toFixed(2)}%`} />
            <Kpi title="Horizon end" value={`${summary.horizonEnd}`} />
          </div>
        )}

        {/* Charts */}
        {rows && rows.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="rounded-2xl shadow-sm">
              <CardContent className="p-6">
                <h3 className="text-lg font-semibold mb-4">Wait time by customer</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={rows}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="Cust" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="Wait" name="Wait" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card className="rounded-2xl shadow-sm">
              <CardContent className="p-6">
                <h3 className="text-lg font-semibold mb-4">Timeline (TSE)</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={rows}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="Cust" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="TSE" name="TSE" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Table */}
        {rows && (
          <Card className="rounded-2xl shadow-sm">
            <CardContent className="p-6 overflow-x-auto">
              <h3 className="text-lg font-semibold mb-4">Results Table</h3>
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left border-b">
                    {[
                      "Cust",
                      "RN_IAT(1-1000)",
                      "IAT",
                      "Arrival",
                      "RN_ST(1-100)",
                      "ST",
                      "TSB",
                      "Wait",
                      "TSE",
                      "TimeInSystem",
                      "ServerIdle",
                    ].map((h) => (
                      <th key={h} className="py-2 pr-4 font-medium text-slate-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.Cust} className="border-b hover:bg-slate-50/70">
                      <td className="py-2 pr-4">{r.Cust}</td>
                      <td className="py-2 pr-4">{r.RN_IAT}</td>
                      <td className="py-2 pr-4">{r.IAT}</td>
                      <td className="py-2 pr-4">{r.Arrival}</td>
                      <td className="py-2 pr-4">{r.RN_ST}</td>
                      <td className="py-2 pr-4">{r.ST}</td>
                      <td className="py-2 pr-4">{r.TSB}</td>
                      <td className="py-2 pr-4">{r.Wait}</td>
                      <td className="py-2 pr-4">{r.TSE}</td>
                      <td className="py-2 pr-4">{r.TimeInSystem}</td>
                      <td className="py-2 pr-4">{r.ServerIdle}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}

        {/* Footer note */}
        <p className="text-xs text-slate-500 text-center pb-8">
          Mapping buckets: IAT RN 1..1000 → 1..8; ST RN 1..100 → 1..6. First arrival starts at time 0.
        </p>
      </div>
    </div>
  );
}

function Kpi({ title, value, suffix }: { title: string; value: string; suffix?: string }) {
  return (
    <Card className="rounded-2xl shadow-sm">
      <CardContent className="p-5">
        <div className="text-xs uppercase tracking-wide text-slate-500">{title}</div>
        <div className="text-2xl font-semibold mt-1">{value}{suffix ?? ""}</div>
      </CardContent>
    </Card>
  );
}

