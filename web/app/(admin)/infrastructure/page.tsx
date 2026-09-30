"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { RefreshCw } from "lucide-react";
import { formatTime } from "@/lib/utils/date";

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

interface VersionInfo {
  app_version: string;
  app_build: string;
  db_schema_version: string;
  content_structure_version: number;
  api_environment: string;
}

export default function InfrastructureStatus() {
  const [health, setHealth] = useState<HealthDeepResponse | null>(null);
  const [versions, setVersions] = useState<VersionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, versionsRes] = await Promise.all([
        fetch("/api/v1/health/deep", { credentials: "include" }),
        fetch("/api/v1/admin/system/versions", { credentials: "include" }),
      ]);

      if (!healthRes.ok) {
        throw new Error(`HTTP ${healthRes.status}: ${healthRes.statusText}`);
      }

      const healthData = await healthRes.json();
      setHealth(healthData);

      if (versionsRes.ok) {
        const versionsData = await versionsRes.json();
        setVersions(versionsData);
      }

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
          <p className="mt-1 text-gray-600">
            Real-time health check for all services. Auto-refreshes every 30 seconds.
          </p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:bg-gray-400"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
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
            {lastUpdated ? `Last updated: ${formatTime(lastUpdated)}` : "Never checked"}
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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
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
                  <div className="text-2xl">{status === "ok" ? "✅" : "❌"}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Version Information */}
      {versions && (
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle className="text-sm">System Versions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-600">App Version:</span>
                <div className="font-mono">{versions.app_version}</div>
              </div>
              <div>
                <span className="text-gray-600">Build:</span>
                <div className="font-mono text-xs">{versions.app_build}</div>
              </div>
              <div>
                <span className="text-gray-600">DB Schema:</span>
                <div className="font-mono">v{versions.db_schema_version}</div>
              </div>
              <div>
                <span className="text-gray-600">Content Structure:</span>
                <div className="font-mono">v{versions.content_structure_version}</div>
              </div>
            </div>
            <div className="mt-3 border-t pt-3">
              <span className="text-xs text-gray-500">
                Environment: {versions.api_environment}
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Info Footer */}
      {health && (
        <Card className="bg-gray-50">
          <CardHeader>
            <CardTitle className="text-sm">API Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">API Version:</span>
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
            <RefreshCw className="mx-auto mb-2 h-8 w-8 animate-spin text-blue-600" />
            <p className="text-gray-600">Fetching health status...</p>
          </div>
        </div>
      )}
    </div>
  );
}
