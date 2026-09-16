import React, { useState, useEffect, useRef } from 'react';
import { HealthStatus, ProviderStatusResponse } from '../../types';
import { Cpu, Plus, Sparkles, Moon, Sun, Key, Check, AlertCircle, X, ChevronDown, Loader2 } from 'lucide-react';
import { fetchProviders, selectProvider, saveAnthropicKey, saveGeminiKey } from '../../services/api';

interface HeaderProps {
  health: HealthStatus | null;
  onNewSession: () => void;
  activeProvider?: 'ollama' | 'anthropic' | 'gemini';
  onProviderChange?: (provider: 'ollama' | 'anthropic' | 'gemini') => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  onNewSession,
  activeProvider: propActiveProvider,
  onProviderChange,
}) => {
  // Theme management (persisted in localStorage)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const saved = window.localStorage.getItem('lenny_growth_theme');
        if (saved === 'dark' || saved === 'light') return saved;
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
          return 'dark';
        }
      }
    } catch {
      // Ignore in non-browser environments
    }
    return 'light';
  });

  useEffect(() => {
    try {
      if (typeof document !== 'undefined') {
        if (theme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      }
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem('lenny_growth_theme', theme);
      }
    } catch {
      // Ignore
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Provider configuration management
  const [isProviderMenuOpen, setIsProviderMenuOpen] = useState(false);
  const [providerData, setProviderData] = useState<ProviderStatusResponse | null>(null);
  const [editingProvider, setEditingProvider] = useState<'gemini' | 'anthropic' | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [isValidatingKey, setIsValidatingKey] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // In browser environment with valid origin, fetch runtime providers
    if (typeof window !== 'undefined' && window.location && window.location.protocol.startsWith('http')) {
      fetchProviders()
        .then(setProviderData)
        .catch(() => {});
    }
  }, []);

  // Close menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsProviderMenuOpen(false);
      }
    };
    if (isProviderMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isProviderMenuOpen]);

  const activeProvider: 'ollama' | 'anthropic' | 'gemini' =
    providerData?.active_provider ||
    propActiveProvider ||
    (health?.provider === 'anthropic' ? 'anthropic' : health?.provider === 'gemini' ? 'gemini' : 'ollama');

  const geminiInfo = providerData?.providers.find((p) => p.id === 'gemini');
  const isGeminiConfigured = geminiInfo ? geminiInfo.configured : false;

  const anthropicInfo = providerData?.providers.find((p) => p.id === 'anthropic');
  const isAnthropicConfigured = anthropicInfo ? anthropicInfo.configured : false;

  const handleSelectProvider = async (p: 'ollama' | 'anthropic' | 'gemini') => {
    setErrorMessage(null);
    setSuccessMessage(null);

    // If cloud provider is NOT configured, active remains unchanged and configuration opens
    if (p === 'gemini' && !isGeminiConfigured) {
      setEditingProvider('gemini');
      setApiKeyInput('');
      return;
    }

    if (p === 'anthropic' && !isAnthropicConfigured) {
      setEditingProvider('anthropic');
      setApiKeyInput('');
      return;
    }

    try {
      const updated = await selectProvider(p);
      setProviderData(updated);
      onProviderChange?.(p);
      setEditingProvider(null);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to switch provider');
    }
  };

  const handleSaveKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKeyInput.trim() || !editingProvider) return;

    setIsValidatingKey(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      let updated: ProviderStatusResponse;
      if (editingProvider === 'gemini') {
        updated = await saveGeminiKey(apiKeyInput.trim());
      } else {
        updated = await saveAnthropicKey(apiKeyInput.trim());
      }

      setProviderData(updated);
      onProviderChange?.(editingProvider);
      setApiKeyInput('');
      const providerLabel = editingProvider === 'gemini' ? 'Google Gemini' : 'Anthropic';
      setSuccessMessage(`${providerLabel} API key validated and activated.`);
      setEditingProvider(null);
    } catch (err: any) {
      // On FAIL: active provider remains unchanged (e.g. Ollama), error is shown
      setErrorMessage(err.message || `Failed to validate ${editingProvider} API key`);
    } finally {
      setIsValidatingKey(false);
    }
  };

  const getProviderBadge = () => {
    if (!health && !providerData) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
          <span className="w-1.5 h-1.5 mr-1.5 bg-slate-400 rounded-full animate-pulse"></span>
          Checking System...
        </span>
      );
    }

    if (activeProvider === 'ollama') {
      return (
        <button
          type="button"
          onClick={() => setIsProviderMenuOpen(!isProviderMenuOpen)}
          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 transition cursor-pointer"
          title="Click to configure generation provider"
          aria-label="Select LLM generation provider"
        >
          <span className="w-1.5 h-1.5 mr-1.5 bg-emerald-500 rounded-full"></span>
          <span>Ollama (llama3.1:8b)</span>
          <ChevronDown className="w-3 h-3 ml-1 text-emerald-600 dark:text-emerald-400 opacity-60" />
        </button>
      );
    }

    if (activeProvider === 'gemini') {
      return (
        <button
          type="button"
          onClick={() => setIsProviderMenuOpen(!isProviderMenuOpen)}
          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800 hover:bg-sky-100 dark:hover:bg-sky-900/60 transition cursor-pointer"
          title="Click to configure generation provider"
          aria-label="Select LLM generation provider"
        >
          <span className="w-1.5 h-1.5 mr-1.5 bg-sky-500 rounded-full"></span>
          <span>Gemini (gemini-2.5-flash)</span>
          <ChevronDown className="w-3 h-3 ml-1 text-sky-600 dark:text-sky-400 opacity-60" />
        </button>
      );
    }

    if (activeProvider === 'anthropic') {
      return (
        <button
          type="button"
          onClick={() => setIsProviderMenuOpen(!isProviderMenuOpen)}
          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 hover:bg-purple-100 dark:hover:bg-purple-900/60 transition cursor-pointer"
          title="Click to configure generation provider"
          aria-label="Select LLM generation provider"
        >
          <span className="w-1.5 h-1.5 mr-1.5 bg-purple-500 rounded-full"></span>
          <span>Anthropic (Claude 3.5 Sonnet)</span>
          <ChevronDown className="w-3 h-3 ml-1 text-purple-600 dark:text-purple-400 opacity-60" />
        </button>
      );
    }

    return (
      <button
        type="button"
        onClick={() => setIsProviderMenuOpen(!isProviderMenuOpen)}
        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/60 transition cursor-pointer"
      >
        <span className="w-1.5 h-1.5 mr-1.5 bg-blue-500 rounded-full"></span>
        {activeProvider}
      </button>
    );
  };

  return (
    <header className="h-14 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 flex items-center justify-between z-20 shrink-0 transition-colors">
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-white font-bold text-sm shadow-sm">
          <Sparkles className="w-4 h-4" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100 tracking-tight">
              The Lenny Growth Assistant
            </h1>
            <span className="text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded">
              Grounded RAG
            </span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 hidden sm:block">
            Verified podcast research & Ship 30 for 30 synthesis
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Provider Selector Menu */}
        <div className="relative" ref={menuRef}>
          <div className="hidden md:flex items-center space-x-2">
            <Cpu className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
            <span className="text-xs text-slate-500 dark:text-slate-400">Active Provider:</span>
            {getProviderBadge()}
          </div>

          {/* Provider Dropdown Popover */}
          {isProviderMenuOpen && (
            <div className="absolute right-0 mt-2 w-80 md:w-96 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-xl z-50 text-xs">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800 mb-3">
                <div>
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                    Generation Provider
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Select reasoning engine for grounded answers
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsProviderMenuOpen(false);
                    setEditingProvider(null);
                  }}
                  className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded"
                  aria-label="Close provider menu"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {errorMessage && (
                <div className="mb-3 p-2 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-900 rounded text-red-700 dark:text-red-300 text-[11px] flex items-center space-x-1.5">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {successMessage && (
                <div className="mb-3 p-2 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-900 rounded text-emerald-700 dark:text-emerald-300 text-[11px] flex items-center space-x-1.5">
                  <Check className="w-3.5 h-3.5 shrink-0" />
                  <span>{successMessage}</span>
                </div>
              )}

              <div className="space-y-2">
                {/* Option 1: Ollama Local */}
                <button
                  type="button"
                  onClick={() => handleSelectProvider('ollama')}
                  className={`w-full p-3 rounded-lg border text-left transition flex items-start justify-between ${
                    activeProvider === 'ollama'
                      ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/40'
                      : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <div>
                    <div className="flex items-center space-x-1.5 font-medium text-slate-900 dark:text-slate-100">
                      <span className="w-2 h-2 rounded-full bg-emerald-500" />
                      <span>Ollama · Local</span>
                      <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-1.5 py-0.2 rounded font-mono">
                        llama3.1:8b
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                      Runs locally inside Docker without internet connection or external API costs.
                    </p>
                  </div>
                  {activeProvider === 'ollama' && (
                    <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  )}
                </button>

                {/* Option 2: Google Gemini Cloud */}
                <div
                  className={`rounded-lg border transition ${
                    activeProvider === 'gemini'
                      ? 'border-sky-500 bg-sky-50/40 dark:bg-sky-950/30'
                      : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => handleSelectProvider('gemini')}
                    className="w-full p-3 text-left flex items-start justify-between"
                  >
                    <div>
                      <div className="flex items-center space-x-1.5 font-medium text-slate-900 dark:text-slate-100">
                        <span className="w-2 h-2 rounded-full bg-sky-500" />
                        <span>Google Gemini · Cloud</span>
                        <span className="text-[10px] bg-sky-100 dark:bg-sky-900/60 text-sky-700 dark:text-sky-300 px-1.5 py-0.2 rounded font-mono">
                          gemini-2.5-flash
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                        High-speed multimodal reasoning and synthesis powered by Google.
                      </p>
                    </div>
                    {activeProvider === 'gemini' && (
                      <Check className="w-4 h-4 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
                    )}
                  </button>

                  {/* Gemini Key Configuration Sub-section */}
                  <div className="px-3 pb-3 pt-1 border-t border-sky-100 dark:border-sky-900/40">
                    {editingProvider !== 'gemini' ? (
                      <div className="flex items-center justify-between text-[11px]">
                        <div className="flex items-center space-x-1.5">
                          <Key className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                          <span className="text-slate-600 dark:text-slate-300">
                            {isGeminiConfigured ? (
                              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                                API Key: Configured
                              </span>
                            ) : (
                              <span className="text-amber-600 dark:text-amber-400 font-medium">
                                API Key: Not Configured
                              </span>
                            )}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingProvider('gemini');
                            setApiKeyInput('');
                            setErrorMessage(null);
                          }}
                          className="text-sky-600 dark:text-sky-400 hover:underline font-medium"
                        >
                          {isGeminiConfigured ? 'Update Key' : 'Configure Key'}
                        </button>
                      </div>
                    ) : (
                      <form onSubmit={handleSaveKey} className="space-y-2 pt-1">
                        <div className="text-[11px] font-medium text-slate-700 dark:text-slate-300 flex items-center justify-between">
                          <span>Enter Google Gemini API Key:</span>
                          <span className="text-[10px] text-slate-400">Validated live</span>
                        </div>
                        <input
                          type="password"
                          value={apiKeyInput}
                          onChange={(e) => setApiKeyInput(e.target.value)}
                          placeholder="AIzaSy..."
                          className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-sky-500"
                          autoFocus
                          disabled={isValidatingKey}
                        />
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingProvider(null);
                              setApiKeyInput('');
                              setErrorMessage(null);
                            }}
                            disabled={isValidatingKey}
                            className="px-2 py-1 text-[11px] text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            disabled={!apiKeyInput.trim() || isValidatingKey}
                            className="inline-flex items-center px-2.5 py-1 text-[11px] font-medium text-white bg-sky-600 hover:bg-sky-700 disabled:opacity-50 rounded shadow-xs"
                          >
                            {isValidatingKey ? (
                              <>
                                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                <span>Validating...</span>
                              </>
                            ) : (
                              <span>Save & Activate</span>
                            )}
                          </button>
                        </div>
                      </form>
                    )}
                  </div>
                </div>

                {/* Option 3: Anthropic Cloud */}
                <div
                  className={`rounded-lg border transition ${
                    activeProvider === 'anthropic'
                      ? 'border-purple-500 bg-purple-50/40 dark:bg-purple-950/30'
                      : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => handleSelectProvider('anthropic')}
                    className="w-full p-3 text-left flex items-start justify-between"
                  >
                    <div>
                      <div className="flex items-center space-x-1.5 font-medium text-slate-900 dark:text-slate-100">
                        <span className="w-2 h-2 rounded-full bg-purple-500" />
                        <span>Anthropic · Cloud</span>
                        <span className="text-[10px] bg-purple-100 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300 px-1.5 py-0.2 rounded font-mono">
                          claude-3-5-sonnet
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                        High-capability cloud model for deeper nuance and complex synthesis.
                      </p>
                    </div>
                    {activeProvider === 'anthropic' && (
                      <Check className="w-4 h-4 text-purple-600 dark:text-purple-400 shrink-0 mt-0.5" />
                    )}
                  </button>

                  {/* Anthropic Key Configuration Sub-section */}
                  <div className="px-3 pb-3 pt-1 border-t border-purple-100 dark:border-purple-900/40">
                    {editingProvider !== 'anthropic' ? (
                      <div className="flex items-center justify-between text-[11px]">
                        <div className="flex items-center space-x-1.5">
                          <Key className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                          <span className="text-slate-600 dark:text-slate-300">
                            {isAnthropicConfigured ? (
                              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                                API Key: Configured
                              </span>
                            ) : (
                              <span className="text-amber-600 dark:text-amber-400 font-medium">
                                API Key: Not Configured
                              </span>
                            )}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingProvider('anthropic');
                            setApiKeyInput('');
                            setErrorMessage(null);
                          }}
                          className="text-purple-600 dark:text-purple-400 hover:underline font-medium"
                        >
                          {isAnthropicConfigured ? 'Update Key' : 'Configure Key'}
                        </button>
                      </div>
                    ) : (
                      <form onSubmit={handleSaveKey} className="space-y-2 pt-1">
                        <div className="text-[11px] font-medium text-slate-700 dark:text-slate-300 flex items-center justify-between">
                          <span>Enter Anthropic API Key:</span>
                          <span className="text-[10px] text-slate-400">Validated live</span>
                        </div>
                        <input
                          type="password"
                          value={apiKeyInput}
                          onChange={(e) => setApiKeyInput(e.target.value)}
                          placeholder="sk-ant-api03-..."
                          className="w-full px-2.5 py-1.5 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
                          autoFocus
                          disabled={isValidatingKey}
                        />
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingProvider(null);
                              setApiKeyInput('');
                              setErrorMessage(null);
                            }}
                            disabled={isValidatingKey}
                            className="px-2 py-1 text-[11px] text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            disabled={!apiKeyInput.trim() || isValidatingKey}
                            className="inline-flex items-center px-2.5 py-1 text-[11px] font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded shadow-xs"
                          >
                            {isValidatingKey ? (
                              <>
                                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                <span>Validating...</span>
                              </>
                            ) : (
                              <span>Save & Activate</span>
                            )}
                          </button>
                        </div>
                      </form>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 text-[10px] text-slate-400 leading-normal">
                Retrieval & embeddings remain strictly fixed to nomic-embed-text over PostgreSQL pgvector.
                Switching providers modifies generation only.
              </div>
            </div>
          )}
        </div>

        {/* Dark / Light Theme Toggle */}
        <button
          type="button"
          onClick={toggleTheme}
          className="p-1.5 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-slate-600" />
          )}
        </button>

        {/* New Session Action */}
        <button
          onClick={onNewSession}
          className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-white bg-brand-500 hover:bg-brand-600 active:bg-brand-700 rounded-md shadow-sm transition-colors"
          aria-label="Create new research session"
        >
          <Plus className="w-3.5 h-3.5 mr-1" />
          <span>New Session</span>
        </button>
      </div>
    </header>
  );
};
