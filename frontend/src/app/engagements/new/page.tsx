'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, FolderGit2, Globe, Loader2, Target } from 'lucide-react';
import Link from 'next/link';
import { engagementsApi, getErrorMessage } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function NewEngagementPage() {
  const router = useRouter();
  const { success, error: toastError } = useToast();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [repoPath, setRepoPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const engagement = await engagementsApi.create({
        name,
        description,
        target_url: targetUrl || undefined,
        repo_path: repoPath || undefined,
      });
      success('Engagement created', `"${engagement.name}" is ready for analysis`);
      router.push(`/engagements/${engagement.id}`);
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      toastError('Failed to create engagement', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <Link
          href="/dashboard"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
        <h1 className="text-2xl font-bold text-white">New Engagement</h1>
        <p className="mt-1 text-sm text-muted">
          Define a security testing scope for AI agents to analyze
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-6 rounded-xl border border-border bg-surface p-6"
      >
        <div>
          <label className="mb-1.5 flex items-center gap-2 text-sm font-medium text-white">
            <Target className="h-4 w-4 text-accent" />
            Engagement Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. API Security Assessment Q3"
            className="w-full"
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-white">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the scope, objectives, and constraints..."
            rows={4}
            className="w-full resize-none"
            required
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 flex items-center gap-2 text-sm font-medium text-white">
              <Globe className="h-4 w-4 text-accent" />
              Target URL
            </label>
            <input
              type="url"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="https://api.example.com"
              className="w-full"
            />
          </div>
          <div>
            <label className="mb-1.5 flex items-center gap-2 text-sm font-medium text-white">
              <FolderGit2 className="h-4 w-4 text-accent" />
              Repository Path
            </label>
            <input
              type="text"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              placeholder="/path/to/repo"
              className="w-full"
            />
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-3 border-t border-border pt-4">
          <Link
            href="/dashboard"
            className="rounded-lg px-4 py-2 text-sm text-muted transition-colors hover:text-white"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Engagement'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
