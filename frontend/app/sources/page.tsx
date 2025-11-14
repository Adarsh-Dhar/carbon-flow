'use client'

import { Card } from '@/components/ui/card'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

const sourceData = [
  { name: 'Stubble Burning', value: 42, color: '#f97316' },
  { name: 'Transport', value: 28, color: '#ef4444' },
  { name: 'Industries', value: 18, color: '#8b5cf6' },
  { name: 'Dust', value: 8, color: '#f59e0b' },
  { name: 'Other', value: 4, color: '#6b7280' },
]

export default function SourcesPage() {
  return (
    <div className="p-8 space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="bg-slate-800/50 border-slate-700 p-6">
          <h2 className="text-slate-50 font-semibold mb-6">Pollution Source Attribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={sourceData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {sourceData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                labelStyle={{ color: '#e2e8f0' }}
                formatter={(value) => `${value}%`}
              />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700 p-6">
          <h3 className="text-slate-50 font-semibold mb-6">Source Breakdown</h3>
          <div className="space-y-4">
            {sourceData.map((source) => (
              <div key={source.name}>
                <div className="flex justify-between mb-1">
                  <span className="text-slate-300 text-sm">{source.name}</span>
                  <span className="text-slate-50 font-semibold">{source.value}%</span>
                </div>
                <div className="w-full bg-slate-700/50 rounded-full h-2">
                  <div
                    className="h-2 rounded-full transition-all"
                    style={{ width: `${source.value}%`, backgroundColor: source.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
