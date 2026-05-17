/**
 * Register.tsx - Registration page
 * Design: Obsidian Precision - Dark tech SaaS
 * Auth: JWT-based registration form
 */

import { useState } from 'react';
import { Link, useLocation } from 'wouter';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Shield,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

const FEATURES = [
  '제한 없는 API 요청',
  '무제한 API 키',
  '전체 탐지 카테고리 (12개)',
  '상세 분석 리포트',
];

export default function Register() {
  const [, navigate] = useLocation();
  const { register, isAuthenticated } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  if (isAuthenticated) {
    navigate('/keys');
    return null;
  }

  const handleChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [field]: e.target.value }));
    if (error) setError('');
  };

  const validate = () => {
    if (!formData.name.trim()) return '이름을 입력해주세요.';
    if (!formData.email.trim()) return '이메일을 입력해주세요.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) return '올바른 이메일 형식이 아닙니다.';
    if (formData.password.length < 8) return '비밀번호는 8자 이상이어야 합니다.';
    if (formData.password !== formData.confirmPassword) return '비밀번호가 일치하지 않습니다.';
    if (!agreedToTerms) return '이용약관에 동의해주세요.';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      await register(formData.name, formData.email, formData.password);
      toast.success('회원가입이 완료되었습니다! 환영합니다.');
      navigate('/keys');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '회원가입에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const passwordStrength = () => {
    const p = formData.password;
    if (!p) return null;
    let score = 0;
    if (p.length >= 8) score++;
    if (p.length >= 12) score++;
    if (/[A-Z]/.test(p)) score++;
    if (/[0-9]/.test(p)) score++;
    if (/[^A-Za-z0-9]/.test(p)) score++;
    if (score <= 1) return { label: '매우 약함', color: 'oklch(0.65 0.22 25)', width: '20%' };
    if (score <= 2) return { label: '약함', color: 'oklch(0.75 0.18 80)', width: '40%' };
    if (score <= 3) return { label: '보통', color: 'oklch(0.75 0.18 80)', width: '60%' };
    if (score <= 4) return { label: '강함', color: 'oklch(0.65 0.18 145)', width: '80%' };
    return { label: '매우 강함', color: 'oklch(0.65 0.18 145)', width: '100%' };
  };

  const strength = passwordStrength();

  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex">
      {/* Left panel - Visual */}
      <div className="hidden lg:flex flex-col justify-center flex-1 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 50%, #EFF6FF 100%)' }}>
        <div className="absolute inset-0 pg-dot-grid opacity-60" />

        <div className="relative z-10 px-12 py-12">
          <div className="max-w-sm">
            <h2 className="text-2xl font-bold tracking-tight text-foreground mb-3">
              무료로 시작하세요
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-8">
              신용카드 없이 즉시 시작할 수 있습니다. 엔터프라이즈급 AI 보안을 무료로 이용하세요.
            </p>

            {/* Features */}
            <div className="space-y-2.5 mb-8">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">주요 기능</p>
              {FEATURES.map(feature => (
                <div key={feature} className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-500" />
                  <span className="text-sm text-foreground">{feature}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right panel - Form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          {/* Logo */}
          <div className="flex items-center gap-2.5 mb-8">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, oklch(0.62 0.22 264), oklch(0.55 0.20 300))' }}>
              <Shield className="w-4.5 h-4.5 text-white" />
            </div>
            <span className="font-semibold">PromptGuard</span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight mb-1">계정 만들기</h1>
          <p className="text-sm text-muted-foreground mb-8">
            무료로 시작하여 AI를 보호하세요.
          </p>

          {/* Error message */}
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-lg mb-4 text-sm"
              style={{ background: 'oklch(0.65 0.22 25 / 0.1)', border: '1px solid oklch(0.65 0.22 25 / 0.3)' }}>
              <AlertCircle className="w-4 h-4 flex-shrink-0" style={{ color: 'oklch(0.75 0.22 25)' }} />
              <span style={{ color: 'oklch(0.80 0.18 25)' }}>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name" className="text-sm">이름</Label>
              <Input
                id="name"
                type="text"
                placeholder="홍길동"
                value={formData.name}
                onChange={handleChange('name')}
                autoComplete="name"
                className="h-10"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm">이메일</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange('email')}
                autoComplete="email"
                className="h-10"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm">비밀번호</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="8자 이상"
                  value={formData.password}
                  onChange={handleChange('password')}
                  autoComplete="new-password"
                  className="h-10 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {/* Password strength */}
              {strength && (
                <div className="space-y-1">
                  <div className="h-1 rounded-full overflow-hidden" style={{ background: '#E5E7EB' }}>
                    <div className="h-full rounded-full transition-all duration-300"
                      style={{ width: strength.width, background: strength.color }} />
                  </div>
                  <p className="text-xs" style={{ color: strength.color }}>{strength.label}</p>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-sm">비밀번호 확인</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="비밀번호 재입력"
                  value={formData.confirmPassword}
                  onChange={handleChange('confirmPassword')}
                  autoComplete="new-password"
                  className="h-10 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                <p className="text-xs" style={{ color: 'oklch(0.75 0.22 25)' }}>비밀번호가 일치하지 않습니다.</p>
              )}
              {formData.confirmPassword && formData.password === formData.confirmPassword && formData.password && (
                <p className="text-xs text-emerald-500 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  비밀번호가 일치합니다.
                </p>
              )}
            </div>

            {/* Terms agreement */}
            <div className="flex items-start gap-2.5">
              <button
                type="button"
                onClick={() => setAgreedToTerms(!agreedToTerms)}
                className={`mt-0.5 w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center transition-all ${
                  agreedToTerms ? 'border-primary' : 'border-border'
                }`}
                style={agreedToTerms ? { background: 'oklch(0.62 0.22 264)' } : {}}
              >
                {agreedToTerms && <CheckCircle2 className="w-3 h-3 text-white" />}
              </button>
              <p className="text-xs text-muted-foreground leading-relaxed">
                <a href="#" className="text-primary hover:underline">이용약관</a>과{' '}
                <a href="#" className="text-primary hover:underline">개인정보처리방침</a>에 동의합니다.
              </p>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-10 gap-2 font-medium"
              style={{ background: 'oklch(0.62 0.22 264)', color: 'white' }}
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  가입 중...
                </>
              ) : (
                <>
                  무료로 시작하기
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground text-center mt-6">
            이미 계정이 있으신가요?{' '}
            <Link href="/login">
              <span className="text-primary hover:underline font-medium">로그인</span>
            </Link>
          </p>

          {/* Security note */}
          <div className="mt-6 flex items-center gap-2 text-xs text-muted-foreground justify-center">
            <Lock className="w-3 h-3" />
            <span>JWT 토큰 기반 인증 · 데이터 암호화 저장</span>
          </div>
        </div>
      </div>
    </div>
  );
}
