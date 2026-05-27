import { Cell, Legend, Pie, PieChart, ResponsiveContainer } from "recharts";

import { Card } from "../Card";

const applicationStatusData = [
  { name: "Applied", value: 18, color: "#6366f1" },
  { name: "Interview", value: 7, color: "#14b8a6" },
  { name: "Offer", value: 2, color: "#f59e0b" },
  { name: "Rejected", value: 5, color: "#f43f5e" },
];

export function ApplicationStatusCard() {
  return (
    <Card title="Application Status">
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={applicationStatusData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="45%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={2}
            >
              {applicationStatusData.map((entry) => (
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
