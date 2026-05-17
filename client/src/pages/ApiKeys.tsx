/**
 * ApiKeys.tsx - API Key Management page
 * Design: Obsidian Precision - Dark tech SaaS
 * Features: List keys, create new key, revoke key, usage stats
 * Auth: Requires login (redirects to /login if not authenticated)
 * Connected to backend endpoints.
 */

import { useState, useEffect } from 'react';
import { Link, useLocation } from 'wouter';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Key,
  Plus,
  Copy,
  Trash2,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Shield,
  Lock,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

interface ApiKey {
  id: string;
  name: string;
  key: string;
  maskedKey: string;
  createdAt: string;
  lastUsed: string | null;
  usageCount: number;
  monthlyLimit: number;
  status: 'active' | 'revoked';
  permissions: string[];
}

interface UserStats {
  today_requests: number;
  month_requests: number;
  avg_response_time_ms: number;
  detection_success_rate: number;
}

interface AuditLog {
  id: number;
  prompt: string;
  risk_score: number;
  action: string;
  process_time_ms: number;
  created_at: string;
}

export default function ApiKeys() {
  const { isAuthenticated, isLoading, user, token } = useAuth();
  const [, navigate] = useLocation();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [stats, setStats] = useState<UserStats>({
    today_requests: 0,
    month_requests: 0,
    avg_response_time_ms: 0,
    detection_success_rate: 99.7,
  });
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showNewKeyDialog, setShowNewKeyDialog] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyValue, setNewKeyValue] = useState('');
  const [deleteKeyId, setDeleteKeyId] = useState<string | null>(null);
  const [revealedKeys, setRevealedKeys] = useState<Set<string>>(new Set());
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, isLoading, navigate]);

  useEffect(() => {
    if (isAuthenticated && token) {
      // Fetch Keys
      fetch('/api/users/keys', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setKeys(data);
        }
      })
      .catch(err => toast.error('API 키를 불러오는데 실패했습니다.'));

      // Fetch Stats
      fetch('/api/users/stats', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(res => res.json())
      .then(data => {
        if (data) {
          setStats(data);
        }
      })
      .catch(err => console.error('통계를 불러오는데 실패했습니다.', err));

      // Fetch Logs
      fetch('/api/users/logs?limit=10', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setLogs(data);
        }
      })
      .catch(err => console.error('로그를 불러오는데 실패했습니다.', err));
    }
  }, [isAuthenticated, token]);

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      toast.error('API 키 이름을 입력해주세요.');
      return;
    }
    setIsCreating(true);
    
    try {
      const res = await fetch('/api/users/keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: newKeyName.trim() })
      });
      if (!res.ok) throw new Error('API 키 생성 실패');
      
      const newKeyObj = await res.json();
      setKeys([...keys, newKeyObj]);
      setNewKeyValue(newKeyObj.key);
      setShowCreateDialog(false);
      setShowNewKeyDialog(true);
      setNewKeyName('');
      toast.success('새 API 키가 생성되었습니다.');
    } catch (error) {
      toast.error('API 키 생성에 실패했습니다.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    try {
      const res = await fetch(`/api/users/keys/${keyId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error('API 키 삭제 실패');
      
      const updated = keys.filter(k => k.id !== keyId);
      setKeys(updated);
      setDeleteKeyId(null);
      toast.success('API 키가 삭제되었습니다.');
    } catch (error) {
      toast.error('API 키 삭제에 실패했습니다.');
    }
  };

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    toast.success('API 키가 클립보드에 복사되었습니다.');
  };

  const toggleReveal = (keyId: string) => {
    setRevealedKeys(prev => {
      const next = new Set(prev);
      if (next.has(keyId)) next.delete(keyId);
      else next.add(keyId);
      return next;
    });
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('ko-KR', {
      year: 'numeric', month: 'short', day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const activeKeys = keys.filter(k => k.status === 'active');

  const USAGE_STATS = [
    { label: '오늘 요청', value: stats.today_requests.toLocaleString(), change: '', positive: true },
    { label: '이번 달 요청', value: stats.month_requests.toLocaleString(), change: '', positive: true },
    { label: '평균 응답시간', value: `${stats.avg_response_time_ms}ms`, change: '', positive: true },
    { label: '탐지 성공률', value: `${stats.detection_success_rate}%`, change: '', positive: true },
  ];

  return (
    <div className="container py-10">
      {/* Page header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight mb-1">API 키 관리</h1>
          <p className="text-sm text-muted-foreground">
            API 키를 생성하고 관리하세요. 무료 서비스이므로 제한 없이 이용하실 수 있습니다.
          </p>
        </div>
        <Button
          onClick={() => setShowCreateDialog(true)}
          className="gap-2 flex-shrink-0"
          style={{ background: '#4F46E5', color: 'white' }}
        >
          <Plus className="w-4 h-4" />
          새 API 키 생성
        </Button>
      </div>

      {/* Usage stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {USAGE_STATS.map((stat, i) => (
          <div key={i} className="pg-card">
            <div className="text-2xl font-bold tracking-tight mb-1">{stat.value}</div>
            <div className="text-xs text-muted-foreground mb-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* API Keys list */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          활성 API 키 ({activeKeys.length})
        </h2>

        {activeKeys.length === 0 ? (
          <div className="pg-card text-center py-12">
            <Key className="w-10 h-10 text-muted-foreground/50 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground mb-4">아직 API 키가 없습니다.</p>
            <Button onClick={() => setShowCreateDialog(true)} size="sm"
              style={{ background: '#4F46E5', color: 'white' }}>
              <Plus className="w-4 h-4 mr-1.5" />
              첫 번째 API 키 생성
            </Button>
          </div>
        ) : (
          activeKeys.map(apiKey => (
            <div key={apiKey.id} className="pg-card pg-card-accent">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  {/* Key name & status */}
                  <div className="flex items-center gap-2 mb-2">
                    <Key className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    <span className="font-medium text-sm">{apiKey.name}</span>
                    <span className="pg-badge-safe text-xs">활성</span>
                  </div>

                  {/* Key value */}
                  <div className="flex items-center gap-2 mb-3">
                    <code className="text-xs font-mono text-muted-foreground bg-secondary px-2.5 py-1.5 rounded-md flex-1 truncate">
                      {revealedKeys.has(apiKey.id) && apiKey.key ? apiKey.key : apiKey.maskedKey}
                    </code>
                    {apiKey.key && (
                      <button
                        onClick={() => toggleReveal(apiKey.id)}
                        className="p-1.5 rounded-md hover:bg-accent transition-colors text-muted-foreground hover:text-foreground flex-shrink-0"
                        title={revealedKeys.has(apiKey.id) ? '숨기기' : '보기'}
                      >
                        {revealedKeys.has(apiKey.id)
                          ? <EyeOff className="w-3.5 h-3.5" />
                          : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    )}
                    <button
                      onClick={() => handleCopyKey(apiKey.key || apiKey.maskedKey)}
                      className="p-1.5 rounded-md hover:bg-accent transition-colors text-muted-foreground hover:text-foreground flex-shrink-0"
                      title="복사"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Usage bar */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
                      <span className="flex items-center gap-1">
                        <Activity className="w-3 h-3" />
                        이번 달 사용량
                      </span>
                      <span>
                        {(apiKey.usageCount || 0).toLocaleString()} 건
                      </span>
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span>생성일: {formatDate(apiKey.createdAt)}</span>
                    <span>마지막 사용: {apiKey.lastUsed ? formatDate(apiKey.lastUsed) : '없음'}</span>
                    <div className="flex items-center gap-1">
                      <Lock className="w-3 h-3" />
                      {(apiKey.permissions || []).join(', ')}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDeleteKeyId(apiKey.id)}
                    className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-1.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    삭제
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}

        {/* Revoked keys */}
        {keys.filter(k => k.status === 'revoked').length > 0 && (
          <>
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mt-6">
              비활성 API 키
            </h2>
            {keys.filter(k => k.status === 'revoked').map(apiKey => (
              <div key={apiKey.id} className="pg-card opacity-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Key className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">{apiKey.name}</span>
                    <span className="pg-badge-danger text-xs">비활성</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteKey(apiKey.id)}
                    className="text-muted-foreground hover:text-destructive gap-1.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    삭제
                  </Button>
                </div>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Audit Logs Section */}
      <div className="mt-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            최근 활동 내역 (Audit Logs)
          </h2>
          <Button variant="ghost" size="sm" className="text-xs gap-1.5" onClick={() => {
            if (token) {
              fetch('/api/users/logs?limit=10', { headers: { 'Authorization': `Bearer ${token}` } })
                .then(res => res.json())
                .then(data => Array.isArray(data) && setLogs(data));
            }
          }}>
            <RefreshCw className="w-3 h-3" />
            새로고침
          </Button>
        </div>

        <div className="pg-card p-0 overflow-hidden border border-border/60">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="bg-muted/30 border-b border-border/60">
                  <th className="px-4 py-3 font-semibold text-xs text-muted-foreground uppercase tracking-wider">시간</th>
                  <th className="px-4 py-3 font-semibold text-xs text-muted-foreground uppercase tracking-wider">프롬프트</th>
                  <th className="px-4 py-3 font-semibold text-xs text-muted-foreground uppercase tracking-wider">위험 점수</th>
                  <th className="px-4 py-3 font-semibold text-xs text-muted-foreground uppercase tracking-wider">결과</th>
                  <th className="px-4 py-3 font-semibold text-xs text-muted-foreground uppercase tracking-wider text-right">응답시간</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                      최근 활동 내역이 없습니다.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-muted-foreground">
                        {new Date(log.created_at).toLocaleString('ko-KR', {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                        })}
                      </td>
                      <td className="px-4 py-3 max-w-[200px] md:max-w-[400px]">
                        <p className="truncate text-xs font-mono bg-muted/50 px-1.5 py-0.5 rounded inline-block">
                          {log.prompt}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                            <div 
                              className="h-full rounded-full" 
                              style={{ 
                                width: `${log.risk_score}%`, 
                                background: log.risk_score > 70 ? '#EF4444' : log.risk_score > 30 ? '#F59E0B' : '#10B981' 
                              }} 
                            />
                          </div>
                          <span className="text-xs font-medium w-8">{Math.round(log.risk_score)}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {log.action === 'blocked' ? (
                          <span className="pg-badge-danger text-[10px] px-1.5 py-0">Blocked</span>
                        ) : (
                          <span className="pg-badge-safe text-[10px] px-1.5 py-0">Allowed</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-muted-foreground font-mono">
                        {log.process_time_ms}ms
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Security tips */}
      <div className="mt-8 pg-card"
        style={{ borderColor: 'rgba(79, 70, 229, 0.2)', background: 'rgba(79, 70, 229, 0.05)' }}>
        <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
          <Shield className="w-4 h-4" style={{ color: '#4F46E5' }} />
          보안 권장사항
        </h3>
        <ul className="space-y-2">
          {[
            'API 키를 환경 변수로 관리하고 코드에 직접 입력하지 마세요.',
            '프로덕션과 개발 환경에 별도의 API 키를 사용하세요.',
            '사용하지 않는 API 키는 즉시 삭제하세요.',
            '키가 노출되었다면 즉시 삭제하고 새 키를 생성하세요.',
          ].map((tip, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
              <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-emerald-500" />
              {tip}
            </li>
          ))}
        </ul>
      </div>

      {/* Create Key Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Key className="w-4 h-4" style={{ color: '#4F46E5' }} />
              새 API 키 생성
            </DialogTitle>
            <DialogDescription>
              API 키에 식별하기 쉬운 이름을 지정하세요.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="key-name">키 이름</Label>
              <Input
                id="key-name"
                placeholder="예: Production API Key"
                value={newKeyName}
                onChange={e => setNewKeyName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCreateKey()}
              />
            </div>
            <div className="rounded-lg border border-border p-3"
              style={{ background: '#F9FAFB' }}>
              <p className="text-xs text-muted-foreground">
                생성된 API 키는 한 번만 표시됩니다. 안전한 곳에 복사해두세요.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowCreateDialog(false)}>취소</Button>
            <Button onClick={handleCreateKey} disabled={isCreating}
              style={{ background: '#4F46E5', color: 'white' }}>
              {isCreating ? (
                <><RefreshCw className="w-4 h-4 mr-1.5 animate-spin" />생성 중...</>
              ) : (
                <><Plus className="w-4 h-4 mr-1.5" />생성하기</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* New Key Display Dialog */}
      <Dialog open={showNewKeyDialog} onOpenChange={setShowNewKeyDialog}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              API 키가 생성되었습니다
            </DialogTitle>
            <DialogDescription>
              아래 API 키를 지금 복사하세요. 이 창을 닫으면 다시 볼 수 없습니다.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="rounded-lg border p-3 flex items-center gap-2"
              style={{ background: '#F9FAFB', borderColor: '#A7F3D0' }}>
              <code className="text-xs font-mono text-foreground flex-1 break-all">{newKeyValue}</code>
              <button
                onClick={() => handleCopyKey(newKeyValue)}
                className="p-1.5 rounded-md hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground flex-shrink-0"
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>
            <div className="flex items-start gap-2 rounded-lg border border-yellow-500/30 p-3"
              style={{ background: 'rgba(245, 158, 11, 0.05)' }}>
              <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-muted-foreground">
                이 키는 다시 표시되지 않습니다. 지금 바로 안전한 곳에 저장하세요.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => { handleCopyKey(newKeyValue); setShowNewKeyDialog(false); }}
              style={{ background: '#4F46E5', color: 'white' }}>
              <Copy className="w-4 h-4 mr-1.5" />
              복사하고 닫기
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteKeyId} onOpenChange={() => setDeleteKeyId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-destructive" />
              API 키 삭제
            </AlertDialogTitle>
            <AlertDialogDescription>
              이 API 키를 삭제하면 해당 키를 사용하는 모든 애플리케이션이 즉시 작동을 멈춥니다.
              이 작업은 되돌릴 수 없습니다.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteKeyId && handleDeleteKey(deleteKeyId)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              삭제하기
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
