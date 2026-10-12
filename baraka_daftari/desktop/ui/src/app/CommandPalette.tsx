import * as Dialog from '@radix-ui/react-dialog';
import { useQueryClient } from '@tanstack/react-query';
import { useState, type KeyboardEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../bindings';

import { PAGE_LINKS, useNav } from './nav';

interface Item {
  id: string;
  label: string;
  run: () => void;
}

/**
 * Buyruqlar palitrasi (Ctrl+K): sahifalar va tezkor amallar. Matn bo'yicha filtr,
 * strelkalar bilan tanlash, Enter — bajarish, Esc — yopish.
 */
export function CommandPalette() {
  const { t } = useTranslation();
  const { paletteOpen, closePalette, setPage, openQuickEntry } = useNav();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);

  const items: Item[] = [
    ...PAGE_LINKS.map((p) => ({
      id: p.id,
      label: t(p.labelKey),
      run: () => {
        setPage(p.id);
      },
    })),
    {
      id: 'quick-entry',
      label: t('palette.quickEntry'),
      run: openQuickEntry,
    },
    {
      id: 'print',
      label: t('palette.print'),
      run: () => {
        window.print();
      },
    },
    {
      id: 'lock',
      label: t('palette.lock'),
      run: () => {
        void commands
          .lock()
          .then(() => queryClient.invalidateQueries({ queryKey: ['vault-state'] }));
      },
    },
  ];

  const q = query.trim().toLowerCase();
  const shown = items.filter((i) => i.label.toLowerCase().includes(q));

  const reset = () => {
    setQuery('');
    setActive(0);
  };
  const choose = (item: Item | undefined) => {
    if (!item) return;
    closePalette();
    reset();
    item.run();
  };
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, shown.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      choose(shown[active]);
    }
  };

  return (
    <Dialog.Root
      open={paletteOpen}
      onOpenChange={(open) => {
        if (!open) {
          closePalette();
          reset();
        }
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50" />
        <Dialog.Content className="fixed left-1/2 top-24 w-full max-w-md -translate-x-1/2 rounded-lg border border-line bg-surface p-4 shadow-xl">
          <Dialog.Title className="sr-only">{t('palette.title')}</Dialog.Title>
          <Dialog.Description className="sr-only">{t('palette.description')}</Dialog.Description>
          <input
            autoFocus
            aria-label={t('palette.title')}
            placeholder={t('palette.placeholder')}
            className="w-full rounded border border-line-strong bg-transparent p-2"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
          />
          <ul role="listbox" className="mt-2 max-h-80 overflow-y-auto">
            {shown.length === 0 && <li className="p-2 text-sm opacity-70">{t('palette.empty')}</li>}
            {shown.map((item, idx) => (
              <li
                key={item.id}
                role="option"
                aria-selected={idx === active}
                className={`cursor-pointer rounded px-3 py-2 ${idx === active ? 'bg-accent text-paper' : ''}`}
                onMouseEnter={() => {
                  setActive(idx);
                }}
                onClick={() => {
                  choose(item);
                }}
              >
                {item.label}
              </li>
            ))}
          </ul>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
