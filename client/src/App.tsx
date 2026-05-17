/**
 * App.tsx - Routes & top-level layout
 * Design: Light theme - Clean white background
 * Routes: / (Home), /docs (API Docs), /keys (API Keys), /login, /register, /analysis-result
 */

import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/NotFound';
import { Route, Switch } from 'wouter';
import ErrorBoundary from './components/ErrorBoundary';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Docs from './pages/Docs';
import ApiKeys from './pages/ApiKeys';
import Login from './pages/Login';
import Register from './pages/Register';
import AnalysisResult from './pages/AnalysisResult';

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <main className="flex-1 pt-14">
        {children}
      </main>
      <Footer />
    </div>
  );
}

function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <main className="flex-1 pt-14">
        {children}
      </main>
    </div>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={() => <Layout><Home /></Layout>} />
      <Route path="/docs" component={() => <Layout><Docs /></Layout>} />
      <Route path="/keys" component={() => <Layout><ApiKeys /></Layout>} />
      <Route path="/analysis-result" component={() => <Layout><AnalysisResult /></Layout>} />
      <Route path="/login" component={() => <AuthLayout><Login /></AuthLayout>} />
      <Route path="/register" component={() => <AuthLayout><Register /></AuthLayout>} />
      <Route path="/404" component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light">
        <AuthProvider>
          <TooltipProvider>
            <Toaster />
            <Router />
          </TooltipProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;

