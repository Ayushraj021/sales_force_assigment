import {
  ArrowUpIcon,
  ArrowDownIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  UsersIcon,
  ShoppingCartIcon,
} from '@heroicons/react/24/outline'
import { ChannelContributionChart } from '@/components/charts/ChannelContributionChart'
import { ForecastChart } from '@/components/charts/ForecastChart'

interface KPICardProps {
  title: string
  value: string
  change: number
  changeLabel: string
  icon: React.ComponentType<{ className?: string }>
}

function KPICard({ title, value, change, changeLabel, icon: Icon }: KPICardProps) {
  const isPositive = change > 0

  return (
    <div className="card card-body">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <div className="p-3 bg-primary-100 rounded-lg">
            <Icon className="h-6 w-6 text-primary-600" />
          </div>
        </div>
        <div className="ml-4 flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
      <div className="mt-4 flex items-center">
        {isPositive ? (
          <ArrowUpIcon className="h-4 w-4 text-green-500" />
        ) : (
          <ArrowDownIcon className="h-4 w-4 text-red-500" />
        )}
        <span
          className={`ml-1 text-sm font-medium ${
            isPositive ? 'text-green-600' : 'text-red-600'
          }`}
        >
          {Math.abs(change)}%
        </span>
        <span className="ml-2 text-sm text-gray-500">{changeLabel}</span>
      </div>
    </div>
  )
}

export function ExecutiveDashboard() {
  // Sample data - in real app, this would come from API
  const kpis = [
    {
      title: 'Total Revenue',
      value: '$1.2M',
      change: 12.5,
      changeLabel: 'vs last month',
      icon: CurrencyDollarIcon,
    },
    {
      title: 'Marketing ROI',
      value: '3.2x',
      change: 8.3,
      changeLabel: 'vs last month',
      icon: ChartBarIcon,
    },
    {
      title: 'New Customers',
      value: '2,847',
      change: -2.1,
      changeLabel: 'vs last month',
      icon: UsersIcon,
    },
    {
      title: 'Conversions',
      value: '12,432',
      change: 15.7,
      changeLabel: 'vs last month',
      icon: ShoppingCartIcon,
    },
  ]

  const channelData = [
    { name: 'Paid Search', contribution: 35, spend: 150000, roi: 4.2 },
    { name: 'Social Media', contribution: 25, spend: 100000, roi: 3.5 },
    { name: 'Display', contribution: 15, spend: 80000, roi: 2.8 },
    { name: 'Email', contribution: 12, spend: 30000, roi: 5.2 },
    { name: 'Affiliate', contribution: 8, spend: 40000, roi: 3.0 },
    { name: 'Organic', contribution: 5, spend: 0, roi: 0 },
  ]

  const forecastData = [
    { date: '2024-01', actual: 980000, forecast: null },
    { date: '2024-02', actual: 1050000, forecast: null },
    { date: '2024-03', actual: 1120000, forecast: null },
    { date: '2024-04', actual: 1200000, forecast: null },
    { date: '2024-05', actual: null, forecast: 1280000 },
    { date: '2024-06', actual: null, forecast: 1350000 },
    { date: '2024-07', actual: null, forecast: 1420000 },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Executive Dashboard</h2>
        <p className="mt-1 text-sm text-gray-500">
          Marketing performance overview and forecasts
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <KPICard key={kpi.title} {...kpi} />
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Channel Contribution */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">
              Channel Contribution
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Marketing channel performance breakdown
            </p>
          </div>
          <div className="card-body">
            <ChannelContributionChart data={channelData} />
          </div>
        </div>

        {/* Revenue Forecast */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">
              Revenue Forecast
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Actual vs predicted revenue
            </p>
          </div>
          <div className="card-body">
            <ForecastChart data={forecastData} />
          </div>
        </div>
      </div>

      {/* Channel Performance Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">
            Channel Performance
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Channel
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contribution
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Spend
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ROI
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {channelData.map((channel) => (
                <tr key={channel.name}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {channel.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <div className="flex items-center">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full"
                          style={{ width: `${channel.contribution}%` }}
                        />
                      </div>
                      {channel.contribution}%
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${channel.spend.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {channel.roi > 0 ? `${channel.roi}x` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
