import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card } from "../Card";

export type ApplicationsOverTimePoint = {
  week: string;
  applications: number;
};

type ApplicationsOverTimeCardProps = {
  data: ApplicationsOverTimePoint[];
};

export function ApplicationsOverTimeCard({ data }: ApplicationsOverTimeCardProps) {
  return (
    <Card title="Applications Over Time">
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="week" stroke="#64748b" />
            <YAxis stroke="#64748b" allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="applications" stroke="#6366f1" strokeWidth={2.5} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
