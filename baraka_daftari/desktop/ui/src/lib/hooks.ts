import { useQuery } from '@tanstack/react-query';

import { commands } from '../bindings';

import { unwrap } from './api';

export function useHome() {
  return useQuery({ queryKey: ['home'], queryFn: () => unwrap(commands.homeSummary()) });
}

export function useMembers() {
  return useQuery({ queryKey: ['members'], queryFn: () => unwrap(commands.listMembers()) });
}

export function useCategories() {
  return useQuery({ queryKey: ['categories'], queryFn: () => unwrap(commands.listCategories()) });
}
