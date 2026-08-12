/**
 * Login and Register pages with robust error extraction & schema-matching validations.
 */
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Brain, Sparkles, Lock, Mail, User as UserIcon, ArrowRight } from 'lucide-react';
import { authApi } from '@/lib/api';
import { useAuthStore } from '@/store';
import { toast } from '@/components/ui/Toast';
import { Spinner } from '@/components/ui/shared';
import { cn } from '@/lib/utils';

function InputField({
  label, id, type = 'text', placeholder, value, onChange, icon, error, rightElement,
}: {
  label: string;
  id: string;
  type?: string;
  placeholder?: string;
  value: string;
  onChange: (v: string) => void;
  icon?: React.ReactNode;
  error?: string;
  rightElement?: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm text-surface-300 font-medium">{label}</label>
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500">
            {icon}
          </div>
        )}
        <input
          id={id}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn('input', icon && 'pl-10', rightElement && 'pr-10', error && 'border-red-500/50')}
        />
        {rightElement && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">{rightElement}</div>
        )}
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

function extractErrorMessage(err: unknown, defaultMsg: string): string {
  if (!err || typeof err !== 'object') return defaultMsg;
  const axiosErr = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };
  const detail = axiosErr.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join('. ');
  }
  return defaultMsg;
}

export function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const e: Record<string, string> = {};
    if (!email) e.email = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(email)) e.email = 'Invalid email';
    if (!password) e.password = 'Password is required';
    return e;
  };

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    setLoading(true);
    try {
      const data = await authApi.login(email, password);
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      const user = await authApi.me();
      setAuth(user, data.access_token, data.refresh_token);
      toast.success(`Welcome back, ${user.username}!`);
      navigate('/chat');
    } catch (err: unknown) {
      const msg = extractErrorMessage(err, 'Login failed');
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-brand-500/10 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md relative"
      >
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-accent-purple flex items-center justify-center animate-glow">
              <Brain className="w-7 h-7 text-white" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-surface-50 mb-1">Welcome back</h1>
          <p className="text-surface-400 text-sm">Sign in to your AI Memory Assistant</p>
        </div>

        <div className="glass rounded-2xl p-8 shadow-xl shadow-surface-950/50">
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <InputField
              label="Email" id="email" type="email"
              placeholder="you@example.com"
              value={email} onChange={setEmail}
              icon={<Mail className="w-4 h-4" />}
              error={errors.email}
            />
            <InputField
              label="Password" id="password" type={showPw ? 'text' : 'password'}
              placeholder="••••••••"
              value={password} onChange={setPassword}
              icon={<Lock className="w-4 h-4" />}
              error={errors.password}
              rightElement={
                <button type="button" onClick={() => setShowPw((s) => !s)} className="text-surface-500 hover:text-surface-300 transition-colors">
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              }
            />
            <button
              type="submit"
              disabled={loading}
              id="login-submit"
              className="btn-primary w-full justify-center py-3"
            >
              {loading ? <Spinner size="sm" /> : (
                <><span>Sign In</span><ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-surface-500 text-sm">
              Don't have an account?{' '}
              <Link to="/register" className="text-brand-400 hover:text-brand-300 font-medium">
                Create one
              </Link>
            </p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-3">
          {[
            { icon: Brain, label: 'Persistent Memory' },
            { icon: Sparkles, label: 'RAG Pipeline' },
            { icon: Lock, label: 'Secure & Private' },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-surface-900/50 border border-surface-800">
              <Icon className="w-4 h-4 text-brand-400" />
              <span className="text-xs text-surface-500">{label}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [form, setForm] = useState({ username: '', email: '', full_name: '', password: '', confirm: '' });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = (k: string) => (v: string) => setForm((f) => ({ ...f, [k]: v }));

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.username) e.username = 'Username is required';
    else if (form.username.length < 3) e.username = 'Min 3 characters';
    else if (!/^[a-zA-Z0-9_-]+$/.test(form.username)) e.username = 'Only letters, numbers, _ and - allowed';
    if (!form.email) e.email = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = 'Invalid email';
    if (!form.password) e.password = 'Password is required';
    else if (form.password.length < 8) e.password = 'Min 8 characters';
    else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) {
      e.password = 'Must contain at least 1 letter and 1 number';
    }
    if (form.password !== form.confirm) e.confirm = 'Passwords do not match';
    return e;
  };

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    setLoading(true);
    try {
      await authApi.register(form.username, form.email, form.password, form.full_name || undefined);
      // Register returns UserResponse (no tokens) — auto-login to get JWT tokens
      const loginData = await authApi.login(form.email, form.password);
      localStorage.setItem('access_token', loginData.access_token);
      localStorage.setItem('refresh_token', loginData.refresh_token);
      const user = await authApi.me();
      setAuth(user, loginData.access_token, loginData.refresh_token);
      toast.success('Account created! Welcome aboard 🎉');
      navigate('/chat');
    } catch (err: unknown) {
      const msg = extractErrorMessage(err, 'Registration failed');
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 right-1/4 w-[500px] h-[500px] bg-accent-purple/8 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md relative"
      >
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-accent-purple flex items-center justify-center">
              <Brain className="w-7 h-7 text-white" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-surface-50 mb-1">Create your account</h1>
          <p className="text-surface-400 text-sm">Start building your AI memory bank</p>
        </div>

        <div className="glass rounded-2xl p-8 shadow-xl shadow-surface-950/50">
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div className="grid grid-cols-2 gap-4">
              <InputField label="Username" id="username" placeholder="johndoe"
                value={form.username} onChange={set('username')} icon={<UserIcon className="w-4 h-4" />} error={errors.username} />
              <InputField label="Full Name" id="full_name" placeholder="John Doe"
                value={form.full_name} onChange={set('full_name')} icon={<UserIcon className="w-4 h-4" />} />
            </div>
            <InputField label="Email" id="reg-email" type="email" placeholder="you@example.com"
              value={form.email} onChange={set('email')} icon={<Mail className="w-4 h-4" />} error={errors.email} />
            <InputField label="Password" id="reg-password" type={showPw ? 'text' : 'password'}
              placeholder="Min 8 chars, 1 letter & 1 number"
              value={form.password} onChange={set('password')} icon={<Lock className="w-4 h-4" />}
              error={errors.password}
              rightElement={
                <button type="button" onClick={() => setShowPw((s) => !s)} className="text-surface-500 hover:text-surface-300 transition-colors">
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              }
            />
            <InputField label="Confirm Password" id="reg-confirm" type="password" placeholder="••••••••"
              value={form.confirm} onChange={set('confirm')} icon={<Lock className="w-4 h-4" />} error={errors.confirm} />

            <button type="submit" disabled={loading} id="register-submit"
              className="btn-primary w-full justify-center py-3 mt-2">
              {loading ? <Spinner size="sm" /> : (
                <><span>Create Account</span><ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-surface-500 text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">Sign in</Link>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
