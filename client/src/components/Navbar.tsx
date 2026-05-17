/**
 * Navbar - Top navigation bar
 * Design: Obsidian Precision - OpenRouter-style dark nav
 * Fixed top, blur backdrop, logo + nav links + auth buttons
 */

import { Link, useLocation } from 'wouter';
import { Shield, Menu, X, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

const navLinks = [
  { href: '/', label: 'Home' },
  { href: '/docs', label: 'API Docs' },
  { href: '/keys', label: 'API Keys' },
];

export default function Navbar() {
  const [location] = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout, isAuthenticated } = useAuth();

  const isActive = (href: string) => {
    if (href === '/') return location === '/';
    return location.startsWith(href);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-border"
      style={{ background: 'rgba(255, 255, 255, 0.92)', backdropFilter: 'blur(12px)' }}>
      <div className="container">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-md flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #4F46E5, #8B5CF6)' }}>
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-sm tracking-tight text-foreground group-hover:text-primary transition-colors">
              PromptGuard
            </span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map(link => (
              <Link key={link.href} href={link.href}>
                <span className={`pg-nav-link text-sm ${isActive(link.href) ? 'active' : ''}`}>
                  {link.label}
                </span>
              </Link>
            ))}
          </nav>

          {/* Right side */}
          <div className="hidden md:flex items-center gap-2">
            {isAuthenticated && user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-accent transition-colors">
                    <Avatar className="w-6 h-6">
                      <AvatarFallback className="text-xs font-medium"
                        style={{ background: 'rgba(79, 70, 229, 0.1)', color: '#4F46E5' }}>
                        {user.name.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <span className="text-sm text-foreground">{user.name}</span>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <div className="px-3 py-2">
                    <p className="text-xs text-muted-foreground">{user.email}</p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link href="/keys">API Keys</Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive">
                    로그아웃
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground">
                    로그인
                  </Button>
                </Link>
                <Link href="/register">
                  <Button size="sm" className="gap-1.5"
                    style={{ background: '#4F46E5', color: 'white' }}>
                    시작하기
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Button>
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu toggle */}
          <button
            className="md:hidden p-2 rounded-md hover:bg-accent transition-colors"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-border/60 bg-background/95 backdrop-blur-sm">
          <div className="container py-4 flex flex-col gap-1">
            {navLinks.map(link => (
              <Link key={link.href} href={link.href} onClick={() => setMobileOpen(false)}>
                <span className={`pg-nav-link block ${isActive(link.href) ? 'active' : ''}`}>
                  {link.label}
                </span>
              </Link>
            ))}
            <div className="pt-3 mt-2 border-t border-border/60 flex flex-col gap-2">
              {isAuthenticated ? (
                <Button variant="ghost" onClick={() => { logout(); setMobileOpen(false); }}
                  className="justify-start text-destructive">
                  로그아웃
                </Button>
              ) : (
                <>
                  <Link href="/login" onClick={() => setMobileOpen(false)}>
                    <Button variant="ghost" className="w-full justify-start">로그인</Button>
                  </Link>
                  <Link href="/register" onClick={() => setMobileOpen(false)}>
                    <Button className="w-full" style={{ background: '#4F46E5', color: 'white' }}>
                      시작하기
                    </Button>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
