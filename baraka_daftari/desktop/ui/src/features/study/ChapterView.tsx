import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands, type TaskDto } from '../../bindings';
import { errorMessage, unwrap } from '../../lib/api';

const MAX_CHARS = 5000;

function TaskRow({ chapterId, task }: { chapterId: string; task: TaskDto }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toggle = useMutation({
    mutationFn: (done: boolean) => unwrap(commands.setTaskDone(chapterId, task.id, done)),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  return (
    <li className="py-2">
      <label className="flex items-start gap-2">
        <input
          type="checkbox"
          className="mt-1"
          checked={task.done}
          disabled={!task.manual || toggle.isPending}
          onChange={(e) => {
            toggle.mutate(e.target.checked);
          }}
        />
        <span>
          {task.title}
          {!task.manual && <span className="ml-2 text-xs opacity-70">{t('study.autoTask')}</span>}
        </span>
      </label>
      {toggle.error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, toggle.error)}
        </p>
      ) : null}
    </li>
  );
}

function DaftarPage({
  chapterId,
  prompt,
  body,
}: {
  chapterId: string;
  prompt: string;
  body: string;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [text, setText] = useState(body);
  useEffect(() => {
    setText(body);
  }, [body, chapterId]);
  const save = useMutation({
    mutationFn: () => unwrap(commands.savePage(chapterId, text)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chapter', chapterId] }),
  });
  return (
    <section
      aria-label={t('study.page')}
      className="rounded-lg border border-accent/30 bg-[repeating-linear-gradient(transparent,transparent_27px,rgba(138,90,28,0.15)_28px)] p-4"
    >
      <h3 className="font-semibold">{t('study.page')}</h3>
      <p className="mt-1 text-sm opacity-80">{prompt}</p>
      <textarea
        aria-label={t('study.page')}
        className="mt-2 h-40 w-full resize-y rounded border border-accent/40 bg-transparent p-2 leading-7"
        maxLength={MAX_CHARS}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
        }}
      />
      <div className="mt-2 flex items-center justify-between text-sm">
        <span className="opacity-70">
          {text.length} / {MAX_CHARS}
        </span>
        <button
          type="button"
          className="rounded bg-accent px-3 py-1 text-paper disabled:opacity-50"
          disabled={save.isPending || text === body}
          onClick={() => {
            save.mutate();
          }}
        >
          {t('study.savePage')}
        </button>
      </div>
      {save.error ? (
        <p role="alert" className="text-sm">
          {errorMessage(t, save.error)}
        </p>
      ) : null}
    </section>
  );
}

/** Bobni o'qish: bloklar, «Daftar sahifasi» va shu haftaning vazifalari. */
export function ChapterView({ id }: { id: string }) {
  const { t } = useTranslation();
  const { data, error } = useQuery({
    queryKey: ['chapter', id],
    queryFn: () => unwrap(commands.chapterDetail(id)),
  });
  if (error) return <p role="alert">{errorMessage(t, error)}</p>;
  if (!data) return null;
  return (
    <article className="space-y-6">
      <header>
        <p className="text-sm opacity-70">{t('study.law', { n: data.law })}</p>
        <h2 className="text-2xl font-semibold">{data.title}</h2>
      </header>
      <div className="space-y-3">
        {data.blocks.map((b) =>
          b.source === null ? (
            <p key={b.id} className={data.placeholder ? 'italic opacity-80' : ''}>
              {b.text}
            </p>
          ) : (
            <blockquote key={b.id} className="border-l-4 border-accent pl-4">
              <p>{b.text}</p>
              <footer className="mt-1 text-sm opacity-70">
                {b.source}
                {b.unreviewed && (
                  <span className="ml-2 rounded bg-accent/20 px-2 py-0.5 text-xs">
                    {t('study.unreviewed')}
                  </span>
                )}
              </footer>
            </blockquote>
          ),
        )}
      </div>
      <p className="text-xs opacity-70">{t('disclaimer')}</p>
      <DaftarPage chapterId={data.id} prompt={data.page_prompt} body={data.page_body} />
      <section>
        <h3 className="font-semibold">{t('study.tasks')}</h3>
        <ul className="divide-y divide-accent/20">
          {data.tasks.map((task) => (
            <TaskRow key={task.id} chapterId={data.id} task={task} />
          ))}
        </ul>
      </section>
    </article>
  );
}
