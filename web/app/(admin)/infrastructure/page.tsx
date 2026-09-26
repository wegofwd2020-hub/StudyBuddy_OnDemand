"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw } from "lucide-react";

interface HealthDeepResponse {
  status: "operational" | "degraded" | "down";
  services: {
    api: "ok" | "error";
    web: "ok" | "error";
    db: "ok" | "error";
    redis: "ok" | "error";
    pgbouncer: "ok" | "error";
    auth0: "ok" | "error";
  };
  version: string;
  build: string;
}

export default function InfrastructureStatus() {
  const [health, setHealth] = useState<HealthDeepResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/health/deep", {
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setHealth(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchHealth();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "ok":
        return "text-green-600";
      case "error":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  const getStatusEmoji = (status: string) => {
    switch (status) {
      case "ok":
        return "✅";
      case "error":
        return "❌";
      default:
        return "⚠️";
    }
  };

  const getOverallStatusColor = (status?: string) => {
    switch (status) {
      case "operational":
        return "bg-green-50 border-green-200";
      case "degraded":
        return "bg-yellow-50 border-yellow-200";
      case "down":
        return "bg-red-50 border-red-200";
      default:
        return "bg-gray-50 border-gray-200";
    }
  };

  const getOverallStatusEmoji = (status?: string) => {
    switch (status) {
      case "operational":
        return "🟢";
      case "degraded":
        return "🟡";
      case "down":
        return "🔴";
      default:
        return "⚪";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Infrastructure Status</h1>
          <p className="text-gray-600 mt-1">
            Real-time health check for all services. Auto-refreshes every 30 seconds.
          </p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Overall Status Card */}
      <Card className={`border-2 ${getOverallStatusColor(health?.status)}`}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-2xl">{getOverallStatusEmoji(health?.status)}</span>
            Overall Status: {health?.status?.toUpperCase() || "UNKNOWN"}
          </CardTitle>
          <CardDescription>
            {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString()}` : "Never checked"}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-700">Connection Error</CardTitle>
            <CardDescription className="text-red-600">{error}</CardDescription>
          </CardHeader>
        </Card>
      )}

      {/* Services Grid */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(health.services).map(([service, status]) => (
            <Card key={service}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold capitalize">{service}</h3>
                    <p className={`text-sm ${getStatusColor(status)}`}>
                      {getStatusEmoji(status)} {status === "ok" ? "Healthy" : "Error"}
                    </p>
                  </div>
                  <div className="text-2xl">
                    {status === "ok" ? "✅" : "❌"}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Info Footer */}
      {health && (
        <Card className="bg-gray-50">
          <CardHeader>
            <CardTitle className="text-sm">System Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Version:</span>
              <span className="font-mono">{health.version}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Build ID:</span>
              <span className="font-mono text-xs">{health.build}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {loading && !health && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-blue-600" />
            <p className="text-gray-600">Fetching health status...</p>
          </div>
        </div>
      )}
    </div>
  );
}
