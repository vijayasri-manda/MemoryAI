/**
 * Settings page — profile, LLM model, embedding config.
 */
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useAuthStore } from '@/store';
import { ChevronLeft, User, Settings, Shield, Bell, Cpu, Database, Trash2, AlertTriangle, Sun, Moon } from 'lucide-react';
import { useUIStore } from '@/store';
import { toast } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

const TABS = [
  { id: 'profile',   label: 'Profile',   icon: User },
  { id: 'appearance', label: 'Appearance', icon: Sun },
  { id: 'model',     label: 'AI Model',  icon: Cpu },
  { id: 'memory',    label: 'Memory',    icon: Database },
  { id: 'security',  label: 'Security',  icon: Shield },
];

export function SettingsPage() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState('profile');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    toast.success('Settings saved successfully');
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="min-h-screen bg-surface-950">
      <header className="sticky top-0 z-10 bg-surface-950/90 backdrop-blur-lg border-b border-surface-700/50">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link to="/chat" className="btn-ghost gap-2">
            <ChevronLeft className="w-4 h-4" />Back
          </Link>
          <div className="flex items-center gap-2.5">
            <Settings className="w-5 h-5 text-brand-400" />
            <h1 className="font-bold text-surface-50">Settings</h1>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-8 flex gap-8">
        {/* Tab nav */}
        <nav className="w-48 shrink-0 space-y-1">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={cn('sidebar-item w-full text-left', id === activeTab && 'active')}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'profile' && (
            <SettingSection title="Profile" description="Update your personal information">
              <SettingField label="Username" id="s-username" defaultValue={user?.username ?? ''} placeholder="johndoe" />
              <SettingField label="Full Name" id="s-fullname" defaultValue={user?.full_name ?? ''} placeholder="John Doe" />
              <SettingField label="Email" id="s-email" type="email" defaultValue={user?.email ?? ''} placeholder="you@example.com" />
            </SettingSection>
          )}

          {activeTab === 'appearance' && (
            <AppearanceSection />
          )}

          {activeTab === 'model' && (
            <SettingSection title="AI Model" description="Configure LLM and embedding settings">
              <div className="space-y-1.5">
                <label className="text-sm text-surface-300 font-medium">LLM Provider</label>
                <select className="input" defaultValue="google">
                  <option value="google">Google Gemini (Gemini 2.5 Flash)</option>
                  <option value="openai">OpenAI (GPT-4o)</option>
                  <option value="anthropic">Anthropic (Claude 3.5)</option>
                  <option value="ollama">Ollama (Local)</option>
                </select>
              </div>
              <SettingField label="Model Name" id="s-model" defaultValue="gemini-2.5-flash" placeholder="gemini-2.5-flash" />
              <div className="space-y-1.5">
                <label className="text-sm text-surface-300 font-medium">Temperature</label>
                <input type="range" min="0" max="1" step="0.05" defaultValue="0.7"
                  className="w-full accent-brand-500" />
                <div className="flex justify-between text-xs text-surface-500"><span>Precise</span><span>Creative</span></div>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm text-surface-300 font-medium">Embedding Model</label>
                <select className="input" defaultValue="sentence_transformers">
                  <option value="sentence_transformers">Sentence Transformers (Local)</option>
                  <option value="openai">OpenAI Embeddings</option>
                  <option value="instructor">Instructor XL</option>
                </select>
              </div>
            </SettingSection>
          )}

          {activeTab === 'memory' && (
            <SettingSection title="Memory Settings" description="Configure how memories are extracted and stored">
              <div className="space-y-1.5">
                <label className="text-sm text-surface-300 font-medium">Vector Store</label>
                <select className="input" defaultValue="chroma">
                  <option value="chroma">ChromaDB (Local)</option>
                  <option value="faiss">FAISS (Local)</option>
                  <option value="pinecone">Pinecone (Cloud)</option>
                  <option value="weaviate">Weaviate (Cloud)</option>
                </select>
              </div>
              <SettingField label="Top-K Memories" id="s-topk" type="number" defaultValue="5" placeholder="5" />
              <SettingField label="Similarity Threshold" id="s-sim" defaultValue="0.65" placeholder="0.65" />
              <SettingField label="Memory TTL (days)" id="s-ttl" type="number" defaultValue="365" placeholder="365 (0 = never)" />
              <SettingToggle id="s-rerank" label="Enable Re-ranking" defaultChecked />
              <SettingToggle id="s-dedup" label="Enable Deduplication" defaultChecked />
              <SettingToggle id="s-compress" label="Enable Context Compression" defaultChecked />

              <div className="mt-6 p-4 rounded-xl bg-red-500/8 border border-red-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <span className="text-sm font-medium text-red-400">Danger Zone</span>
                </div>
                <p className="text-xs text-surface-500 mb-3">These actions are irreversible.</p>
                <button className="btn-danger text-xs gap-1.5" onClick={() => toast.error('Confirm this action in a production app with extra validation')}>
                  <Trash2 className="w-3.5 h-3.5" />Clear All Memories
                </button>
              </div>
            </SettingSection>
          )}

          {activeTab === 'security' && (
            <SettingSection title="Security" description="Manage your account security">
              <SettingField label="Current Password" id="s-curpw" type="password" placeholder="••••••••" />
              <SettingField label="New Password" id="s-newpw" type="password" placeholder="Min 8 characters" />
              <SettingField label="Confirm New Password" id="s-confirmpw" type="password" placeholder="••••••••" />
              <div className="pt-4 border-t border-surface-700/50">
                <h4 className="text-sm font-medium text-surface-200 mb-1">Two-Factor Authentication</h4>
                <p className="text-xs text-surface-500 mb-3">Add an extra layer of security to your account.</p>
                <button className="btn-ghost text-sm border border-surface-600 px-4 py-2">Enable 2FA</button>
              </div>
            </SettingSection>
          )}

          <div className="mt-6 flex justify-end">
            <button onClick={handleSave} className="btn-primary px-6 py-2.5">
              {saved ? '✓ Saved!' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function AppearanceSection() {
  const { theme, setTheme } = useUIStore();

  return (
    <SettingSection title="Appearance" description="Customize the application look & feel">
      <div className="grid grid-cols-2 gap-4 pt-2">
        <button
          onClick={() => setTheme('dark')}
          className={cn(
            'p-4 rounded-2xl border flex flex-col items-center gap-3 transition-all cursor-pointer text-left',
            theme === 'dark'
              ? 'bg-brand-500/15 border-brand-500 ring-2 ring-brand-500/50'
              : 'bg-surface-800/50 border-surface-700/50 hover:bg-surface-700/50'
          )}
        >
          <div className="w-10 h-10 rounded-xl bg-surface-900 flex items-center justify-center">
            <Moon className="w-5 h-5 text-accent-purple" />
          </div>
          <div className="text-center">
            <p className="font-semibold text-sm text-surface-50">Dark Mode</p>
            <p className="text-xs text-surface-400">Sleek, high-contrast dark aesthetic</p>
          </div>
        </button>

        <button
          onClick={() => setTheme('light')}
          className={cn(
            'p-4 rounded-2xl border flex flex-col items-center gap-3 transition-all cursor-pointer text-left',
            theme === 'light'
              ? 'bg-brand-500/15 border-brand-500 ring-2 ring-brand-500/50'
              : 'bg-surface-800/50 border-surface-700/50 hover:bg-surface-700/50'
          )}
        >
          <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
            <Sun className="w-5 h-5 text-amber-500" />
          </div>
          <div className="text-center">
            <p className="font-semibold text-sm text-surface-50">Light Mode</p>
            <p className="text-xs text-surface-400">Bright and clean interface</p>
          </div>
        </button>
      </div>
    </SettingSection>
  );
}

function SettingSection({ title, description, children }: {
  title: string; description: string; children: React.ReactNode;
}) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-5">
      <div className="border-b border-surface-700/50 pb-4">
        <h2 className="text-lg font-semibold text-surface-50">{title}</h2>
        <p className="text-sm text-surface-400">{description}</p>
      </div>
      {children}
    </motion.div>
  );
}

function SettingField({ label, id, type = 'text', defaultValue, placeholder }: {
  label: string; id: string; type?: string; defaultValue?: string; placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm text-surface-300 font-medium">{label}</label>
      <input id={id} type={type} defaultValue={defaultValue} placeholder={placeholder} className="input" />
    </div>
  );
}

function SettingToggle({ id, label, defaultChecked }: { id: string; label: string; defaultChecked?: boolean }) {
  const [checked, setChecked] = useState(defaultChecked ?? false);
  return (
    <div className="flex items-center justify-between py-1">
      <label htmlFor={id} className="text-sm text-surface-300">{label}</label>
      <button
        id={id}
        role="switch"
        aria-checked={checked}
        onClick={() => setChecked((s) => !s)}
        className={cn(
          'w-10 h-6 rounded-full transition-colors duration-200 relative',
          checked ? 'bg-brand-500' : 'bg-surface-700',
        )}
      >
        <span className={cn(
          'absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200',
          checked && 'translate-x-4',
        )} />
      </button>
    </div>
  );
}
