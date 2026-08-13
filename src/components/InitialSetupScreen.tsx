import React, { useState } from 'react';
import { Shield, Key, UserCheck, ArrowRight, CheckCircle2, Lock, Terminal, Copy, Check } from 'lucide-react';
import { apiService } from '../services/api';

interface InitialSetupScreenProps {
  onSetupComplete: () => void;
}

export const InitialSetupScreen: React.FC<InitialSetupScreenProps> = ({ onSetupComplete }) => {
  const [step, setStep] = useState<1 | 2>(1);
  const [initialPassword, setInitialPassword] = useState('');
  const [username, setUsername] = useState('admin');
  const [email, setEmail] = useState('admin@skyops.internal');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const kubectlCommand = 'kubectl get secret skyops-secrets -n skyops-system -o jsonpath="{.data.initial-admin-password}" | base64 --decode';

  const handleCopyCommand = () => {
    navigator.clipboard.writeText(kubectlCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleVerifyInitialPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!initialPassword.trim()) {
      setError('Please enter the initial administrator password.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await apiService.verifyInitialPassword(initialPassword.trim());
      setStep(2);
    } catch (err: any) {
      setError(err.message || 'Invalid initial administrator password.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('Username is required.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await apiService.setupAdmin({
        initial_password: initialPassword.trim(),
        username: username.trim(),
        email: email.trim() || undefined,
        password,
      });
      onSetupComplete();
    } catch (err: any) {
      setError(err.message || 'Failed to create administrator account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4 sm:p-6 select-none font-sans text-slate-100">
      {/* Background Decorative Blur */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-lg bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl backdrop-blur-xl p-8 relative overflow-hidden z-10">
        {/* Header Branding */}
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="w-14 h-14 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/20 mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            SkyOps <span className="text-cyan-400 font-semibold text-xs px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/50">V1 Setup</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            First-time Administrator Initialization
          </p>
        </div>

        {/* Progress Tracker */}
        <div className="flex items-center justify-between mb-8 px-4 relative">
          <div className="absolute top-1/2 left-10 right-10 h-0.5 bg-slate-800 -translate-y-1/2 z-0" />
          
          {/* Step 1 */}
          <div className="relative z-10 flex flex-col items-center">
            <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${
              step >= 1 ? 'bg-cyan-500 text-slate-950 ring-4 ring-cyan-500/20 shadow-lg shadow-cyan-500/30' : 'bg-slate-800 text-slate-400'
            }`}>
              {step > 1 ? <CheckCircle2 className="w-5 h-5 text-slate-950" /> : '1'}
            </div>
            <span className={`text-xs mt-2 font-medium ${step >= 1 ? 'text-cyan-400' : 'text-slate-500'}`}>
              Verify Password
            </span>
          </div>

          {/* Step 2 */}
          <div className="relative z-10 flex flex-col items-center">
            <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${
              step === 2 ? 'bg-cyan-500 text-slate-950 ring-4 ring-cyan-500/20 shadow-lg shadow-cyan-500/30' : 'bg-slate-800 text-slate-400'
            }`}>
              2
            </div>
            <span className={`text-xs mt-2 font-medium ${step === 2 ? 'text-cyan-400' : 'text-slate-500'}`}>
              Create Account
            </span>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-sm flex items-start gap-3">
            <Shield className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Authentication Error</p>
              <p className="text-xs text-rose-300/90 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* STEP 1: Enter Initial Password */}
        {step === 1 && (
          <form onSubmit={handleVerifyInitialPassword} className="space-y-6">
            <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
                <span className="flex items-center gap-1.5 text-cyan-400">
                  <Terminal className="w-4 h-4" /> Kubernetes Secret Command
                </span>
                <button
                  type="button"
                  onClick={handleCopyCommand}
                  className="text-slate-400 hover:text-white flex items-center gap-1 transition"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <p className="text-xs text-slate-400 font-mono bg-slate-900 p-2.5 rounded-lg border border-slate-800 overflow-x-auto select-all">
                {kubectlCommand}
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                Retrieve the auto-generated initial password from the deployed Helm secret.
              </p>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Key className="w-4 h-4 text-cyan-400" /> Initial Administrator Password
                </label>
                <button
                  type="button"
                  onClick={() => setInitialPassword('skyops123')}
                  className="text-xs text-cyan-400 hover:text-cyan-300 font-mono bg-cyan-950/60 hover:bg-cyan-900/80 px-2 py-0.5 rounded border border-cyan-800/60 transition cursor-pointer"
                >
                  Quick Fill Dev Password (skyops123)
                </button>
              </div>
              <input
                type="password"
                value={initialPassword}
                onChange={(e) => setInitialPassword(e.target.value)}
                placeholder="Enter password (default: skyops123)"
                className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono text-sm transition"
                required
              />
              <p className="text-[11px] text-slate-400 mt-1.5 flex items-center gap-1">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>Default local testing password: <code className="bg-slate-900 px-1 py-0.5 rounded text-cyan-300 font-mono">skyops123</code></span>
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold rounded-xl shadow-lg shadow-cyan-500/20 transition-all duration-200 flex items-center justify-center gap-2 text-sm disabled:opacity-50"
            >
              {loading ? 'Verifying...' : (
                <>
                  Verify & Proceed <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        )}

        {/* STEP 2: Create Administrator Account */}
        {step === 2 && (
          <form onSubmit={handleCreateAdmin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. admin"
                className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm transition"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Email Address (Optional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@skyops.internal"
                className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                New Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 6 characters"
                className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm font-mono transition"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm font-mono transition"
                required
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold rounded-xl shadow-lg shadow-cyan-500/20 transition-all duration-200 flex items-center justify-center gap-2 text-sm disabled:opacity-50"
              >
                {loading ? 'Creating Administrator...' : (
                  <>
                    <UserCheck className="w-4 h-4" /> Complete Setup & Continue
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
