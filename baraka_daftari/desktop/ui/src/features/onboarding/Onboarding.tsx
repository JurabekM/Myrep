import * as Dialog from '@radix-ui/react-dialog';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { commands } from '../../bindings';
import { unwrap } from '../../lib/api';

/** Birinchi ishga tushirishdagi qisqa tanishtiruv: 5 qadam, istalgan paytda o'tkazib yuborish mumkin. */
const STEPS = ['welcome', 'income', 'vault', 'havas', 'safety'] as const;

export function Onboarding() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const done = useQuery({
    queryKey: ['onboarding'],
    queryFn: () => unwrap(commands.onboardingDone()),
  });
  const [step, setStep] = useState(0);
  const finish = useMutation({
    mutationFn: () => unwrap(commands.completeOnboarding()),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['onboarding'] }),
  });
  if (done.data !== false) return null;
  const key = STEPS[step] ?? 'welcome';
  const last = step === STEPS.length - 1;
  return (
    <Dialog.Root open>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40" />
        <Dialog.Content
          className="fixed left-1/2 top-24 w-full max-w-lg -translate-x-1/2 rounded-lg bg-paper p-6 shadow-xl"
          onEscapeKeyDown={(e) => {
            e.preventDefault();
          }}
          onInteractOutside={(e) => {
            e.preventDefault();
          }}
        >
          <p className="text-xs opacity-70" data-testid="onb-progress">
            {t('onboarding.progress', { n: step + 1, total: STEPS.length })}
          </p>
          <Dialog.Title className="mt-1 text-lg font-semibold">
            {t(`onboarding.steps.${key}.title`)}
          </Dialog.Title>
          <Dialog.Description className="mt-2 text-sm">
            {t(`onboarding.steps.${key}.body`)}
          </Dialog.Description>
          <div className="mt-5 flex items-center justify-between">
            <button
              type="button"
              className="underline"
              onClick={() => {
                finish.mutate();
              }}
            >
              {t('onboarding.skip')}
            </button>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded border border-accent px-3 py-1"
                disabled={step === 0}
                onClick={() => {
                  setStep(step - 1);
                }}
              >
                {t('onboarding.back')}
              </button>
              <button
                type="button"
                className="rounded bg-accent px-3 py-1 text-paper"
                onClick={() => {
                  if (last) finish.mutate();
                  else setStep(step + 1);
                }}
              >
                {last ? t('onboarding.finish') : t('onboarding.next')}
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
