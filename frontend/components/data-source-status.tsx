interface DataSourceStatusProps {
  sources: Array<{
    name: string
    active: boolean
    lastUpdate?: string
  }>
}

export default function DataSourceStatus({ sources }: DataSourceStatusProps) {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
      <h3 className="text-slate-50 font-semibold mb-4">Data Source Status</h3>
      <div className="space-y-3">
        {sources.map((source) => (
          <div key={source.name} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${source.active ? 'bg-green-400' : 'bg-slate-500'}`} />
              <div>
                <p className="text-slate-300 text-sm font-medium">{source.name}</p>
                {source.lastUpdate && (
                  <p className="text-slate-500 text-xs">{source.lastUpdate}</p>
                )}
              </div>
            </div>
            <span className="text-xs font-semibold text-slate-400">
              {source.active ? 'Active' : 'Inactive'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
