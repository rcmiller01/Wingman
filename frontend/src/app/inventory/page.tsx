'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface DockerContainer {
    id: string;
    name: string;
    image: string;
    state: string;
    status: string;
    stats?: {
        cpuPercent: number;
        memoryUsageMb: number;
        memoryLimitMb: number;
        memoryPercent: number;
    };
}

interface ProxmoxVM {
    vmid: number;
    name: string;
    node: string;
    type: 'qemu' | 'lxc';
    status: string;
}

interface ProxmoxNode {
    node: string;
    status: string;
}

interface InventoryData {
    docker: { available: boolean; containers: DockerContainer[] };
    proxmox: { available: boolean; configured: boolean; nodes: ProxmoxNode[]; vms: ProxmoxVM[] };
    collector: { running: boolean; intervalSeconds: number };
}

export default function InventoryPage() {
    const router = useRouter();
    const [inventory, setInventory] = useState<InventoryData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'docker' | 'proxmox'>('docker');

    useEffect(() => {
        async function fetchInventory() {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';
                const res = await fetch(`${apiUrl}/api/inventory`);
                const data = await res.json();
                setInventory(data);
                setError(null);
            } catch (err) {
                setError('Failed to connect to backend');
            } finally {
                setLoading(false);
            }
        }

        fetchInventory();
        const interval = setInterval(fetchInventory, 10000);
        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (state: string) => {
        switch (state.toLowerCase()) {
            case 'running':
            case 'online':
                return 'bg-emerald-500';
            case 'stopped':
            case 'offline':
                return 'bg-slate-500';
            case 'paused':
                return 'bg-yellow-500';
            default:
                return 'bg-slate-600';
        }
    };

    const getStatusBadge = (state: string) => {
        const color = getStatusColor(state);
        return (
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${state.toLowerCase() === 'running' || state.toLowerCase() === 'online'
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-slate-600/50 text-slate-300'
                }`}>
                <span className={`w-2 h-2 rounded-full ${color}`} />
                {state}
            </span>
        );
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="flex items-center gap-3 text-slate-400">
                    <div className="w-5 h-5 border-2 border-copilot-500 border-t-transparent rounded-full animate-spin" />
                    Loading inventory...
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Inventory</h1>
                    <p className="text-slate-400">Infrastructure resources and status</p>
                </div>
                {inventory?.collector && (
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                        <span className={`w-2 h-2 rounded-full ${inventory.collector.running ? 'bg-emerald-500' : 'bg-slate-500'}`} />
                        Collector: {inventory.collector.running ? 'Running' : 'Stopped'}
                        <span className="text-slate-600">|</span>
                        <span>Every {inventory.collector.intervalSeconds}s</span>
                    </div>
                )}
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
                    {error}
                </div>
            )}

            {/* Tabs */}
            <div className="flex gap-2">
                <button
                    onClick={() => setActiveTab('docker')}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'docker'
                        ? 'bg-copilot-600 text-white'
                        : 'bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-700/50'
                        }`}
                >
                    🐳 Docker
                    {inventory?.docker.available && (
                        <span className="ml-2 px-2 py-0.5 bg-white/10 rounded text-xs">
                            {inventory.docker.containers.length}
                        </span>
                    )}
                </button>
                <button
                    onClick={() => setActiveTab('proxmox')}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'proxmox'
                        ? 'bg-copilot-600 text-white'
                        : 'bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-700/50'
                        }`}
                >
                    🖥️ Proxmox
                    {inventory?.proxmox.available && (
                        <span className="ml-2 px-2 py-0.5 bg-white/10 rounded text-xs">
                            {inventory.proxmox.vms.length}
                        </span>
                    )}
                </button>
            </div>

            {/* Docker Tab */}
            {activeTab === 'docker' && (
                <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 overflow-hidden">
                    {!inventory?.docker.available ? (
                        <div className="p-8 text-center text-slate-400">
                            <p className="text-lg mb-2">Docker not available</p>
                            <p className="text-sm">Make sure Docker is running and accessible</p>
                        </div>
                    ) : inventory.docker.containers.length === 0 ? (
                        <div className="p-8 text-center text-slate-400">
                            <p>No containers found</p>
                        </div>
                    ) : (
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-700/50">
                                    <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">Name</th>
                                    <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">Image</th>
                                    <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">Status</th>
                                    <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">CPU</th>
                                    <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">Memory</th>
                                </tr>
                            </thead>
                            <tbody>
                                {inventory.docker.containers.map((container) => (
                                    <tr
                                        key={container.id}
                                        className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors cursor-pointer"
                                        onClick={() => router.push(`/inventory/docker/${container.id}`)}
                                    >
                                        <td className="px-6 py-4">
                                            <div className="text-white font-medium">{container.name}</div>
                                            <div className="text-slate-500 text-xs font-mono">{container.id.substring(0, 12)}</div>
                                        </td>
                                        <td className="px-6 py-4 text-slate-300 text-sm">{container.image}</td>
                                        <td className="px-6 py-4">{getStatusBadge(container.state)}</td>
                                        <td className="px-6 py-4 text-slate-300 text-sm">
                                            {container.stats ? `${container.stats.cpuPercent.toFixed(1)}%` : '-'}
                                        </td>
                                        <td className="px-6 py-4 text-slate-300 text-sm">
                                            {container.stats
                                                ? `${container.stats.memoryUsageMb}MB / ${container.stats.memoryLimitMb}MB`
                                                : '-'
                                            }
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {/* Proxmox Tab */}
            {activeTab === 'proxmox' && (
                <div className="space-y-6">
                    {!inventory?.proxmox.configured ? (
                        <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-8 text-center">
                            <p className="text-lg text-slate-400 mb-2">Proxmox not configured</p>
                            <p className="text-sm text-slate-500">
                                Set PROXMOX_HOST, PROXMOX_USER, PROXMOX_TOKEN_NAME, and PROXMOX_TOKEN_VALUE in .env
                            </p>
                        </div>
                    ) : !inventory.proxmox.available ? (
                        <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-8 text-center text-slate-400">
                            <p className="text-lg mb-2">Proxmox not reachable</p>
                            <p className="text-sm">Check your connection settings</p>
                        </div>
                    ) : (
                        <>
                            {/* Nodes */}
                            <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-6">
                                <h2 className="text-white font-semibold mb-4">Nodes ({inventory.proxmox.nodes.length})</h2>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    {inventory.proxmox.nodes.map((node) => (
                                        <div key={node.node} className="bg-slate-700/30 rounded-xl p-4">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-white font-medium">{node.node}</span>
                                                {getStatusBadge(node.status)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* VMs and LXCs */}
                            <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-slate-700/50 overflow-hidden">
                                <table className="w-full">
                                    <thead>
                                        <tr className="border-b border-slate-700/50">
                                            <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">Name</th>
                                            <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">Type</th>
                                            <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">Node</th>
                                            <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">Status</th>
                                            <th className="text-left text-slate-400 text-sm font-medium px-6 py-4">VMID</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {inventory.proxmox.vms.map((vm) => (
                                            <tr key={`${vm.node}-${vm.vmid}`} className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors">
                                                <td className="px-6 py-4 text-white font-medium">{vm.name}</td>
                                                <td className="px-6 py-4">
                                                    <span className={`px-2 py-1 rounded text-xs ${vm.type === 'qemu'
                                                        ? 'bg-purple-500/20 text-purple-400'
                                                        : 'bg-blue-500/20 text-blue-400'
                                                        }`}>
                                                        {vm.type === 'qemu' ? 'VM' : 'LXC'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-slate-300 text-sm">{vm.node}</td>
                                                <td className="px-6 py-4">{getStatusBadge(vm.status)}</td>
                                                <td className="px-6 py-4 text-slate-500 text-sm font-mono">{vm.vmid}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
