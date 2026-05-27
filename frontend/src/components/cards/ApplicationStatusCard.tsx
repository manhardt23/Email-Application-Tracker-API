import { Cell, Legend, Pie, PieChart, ResponsiveContainer } from "recharts";

import { Card } from "../Card";

export type ApplicationStatusPoint = {
  name: "Applied" | "Interview" | "Offer" | "Rejected";
  value: number;
  color: string;
};

type ApplicationStatusCardProps = {
  data: ApplicationStatusPoint[];
};

export function ApplicationStatusCard({ data }: ApplicationStatusCardProps) {
  return (
    <Card title="Application Status">
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="45%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={2}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Legend verticalAlign="bottom" />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
