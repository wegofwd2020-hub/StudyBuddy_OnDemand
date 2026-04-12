"use client";

/**
 * /admin/demo-settings
 *
 * PLAT-ADMIN console for geo-block management.
 * Add or remove country codes from the demo request block list.
 *
 * Requires: sb_admin_token with plat_admin role (demo:manage permission).
 */

import { useState } from "react";
import {
  listDemoGeoBlocks,
  addDemoGeoBlock,
  removeDemoGeoBlock,
  type GeoBlockItem,
} from "@/lib/api/admin";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Shield, Trash2, Plus, ArrowLeft } from "lucide-react";

function GeoBlockRow({ block }: { block: GeoBlockItem }) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  const removeMut = useMutation({
    mutationFn: () => removeDemoGeoBlock(block.country_code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["demo-geo-blocks"] });
    },
  });

  return (
    <div className="flex items-center gap-3 border-b px-4 py-3 last:border-0">
      <span className="w-12 font-mono text-sm font-bold text-gray-700">
        {block.country_code}
      </span>
      <span className="flex-1 text-sm text-gray-600">
        {block.country_name ?? "—"}
      </span>
      <span className="text-xs text-gray-400">
        {new Date(block.added_at).toLocaleDateString()}
      </span>
      {confirming ? (
        <div className="flex gap-2">
          <button
            onClick={() => removeMut.mutate()}
            disabled={removeMut.isPending}
            className="rounded bg-red-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50"
          >
            {removeMut.isPending ? "Removing…" : "Remove"}
          </button>
          <button
            onClick={() => setConfirming(false)}
            className="rounded border border-gray-200 px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setConfirming(true)}
          className="text-gray-400 hover:text-red-500"
          title="Remove geo-block"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

function AddBlockForm() {
  const [countryCode, setCountryCode] = useState("");
  const [countryName, setCountryName] = useState("");
  const [error, setError] = useState("");
  const queryClient = useQueryClient();

  const addMut = useMutation({
    mutationFn: () =>
      addDemoGeoBlock(
        countryCode.toUpperCase().trim(),
        countryName.trim() || undefined,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["demo-geo-blocks"] });
      setCountryCode("");
      setCountryName("");
      setError("");
    },
    onError: () => {
      setError("Failed to add. Check the country code and try again.");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const code = countryCode.trim().toUpperCase();
    if (!/^[A-Z]{2}$/.test(code)) {
      setError("Country code must be exactly 2 letters (ISO 3166-1 alpha-2).");
      return;
    }
    setError("");
    addMut.mutate();
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3 p-4">
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Country code *
        </label>
        <input
          value={countryCode}
          onChange={(e) => setCountryCode(e.target.value)}
          placeholder="e.g. CN"
          maxLength={2}
          className="w-20 rounded border border-gray-200 px-2.5 py-1.5 font-mono text-sm uppercase focus:outline-none focus:ring-1 focus:ring-gray-400"
        />
      </div>
      <div className="flex-1">
        <label className="mb-1 block text-xs font-medium text-gray-600">
          Country name (optional)
        </label>
        <input
          value={countryName}
          onChange={(e) => setCountryName(e.target.value)}
          placeholder="e.g. China"
          className="w-full rounded border border-gray-200 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400"
        />
      </div>
      <button
        type="submit"
        disabled={addMut.isPending || !countryCode.trim()}
        className="flex items-center gap-1.5 rounded bg-gray-900 px-4 py-1.5 text-sm font-semibold text-white hover:bg-gray-700 disabled:opacity-50"
      >
        <Plus className="h-4 w-4" />
        {addMut.isPending ? "Adding…" : "Add block"}
      </button>
      {error && (
        <p className="ml-1 text-xs text-red-600">{error}</p>
      )}
    </form>
  );
}

export default function DemoSettingsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["demo-geo-blocks"],
    queryFn: listDemoGeoBlocks,
  });

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <div className="mb-6">
        <a
          href="/admin/demo-leads"
          className="mb-4 flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to demo leads
        </a>
        <div className="flex items-center gap-3">
          <Shield className="h-6 w-6 text-gray-400" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Geo-block settings</h1>
            <p className="mt-0.5 text-sm text-gray-500">
              Demo tour requests from blocked countries are silently rejected at
              the IP-lookup stage.
            </p>
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="border-b bg-gray-50 px-4 py-2.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            Blocked countries ({data?.blocks.length ?? 0})
          </p>
        </div>

        {isLoading && (
          <div className="px-4 py-6 text-center text-sm text-gray-400">
            Loading…
          </div>
        )}
        {isError && (
          <div className="px-4 py-6 text-center text-sm text-red-500">
            Failed to load geo-blocks.
          </div>
        )}
        {data && data.blocks.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-gray-400">
            No countries blocked.
          </div>
        )}
        {data &&
          data.blocks.map((block) => (
            <GeoBlockRow key={block.country_code} block={block} />
          ))}

        <div className="border-t bg-gray-50">
          <AddBlockForm />
        </div>
      </div>
    </div>
  );
}
