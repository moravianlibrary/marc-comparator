import { useMutation } from '@tanstack/react-query';
import type { LucideIcon } from 'lucide-react';
import { Loader2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useInvalidateTasks } from '@/hooks/use-invalidate-tasks';
import apiClient from '@/lib/api-client';

interface MaintenanceActionCardProps {
  icon: LucideIcon;
  titleKey: string;
  descriptionKey: string;
  endpoint: string;
  showMaxAge?: boolean;
}

export function MaintenanceActionCard({
  icon: Icon,
  titleKey,
  descriptionKey,
  endpoint,
  showMaxAge = false,
}: MaintenanceActionCardProps) {
  const { t } = useTranslation('maintenance');
  const [maxAgeDays, setMaxAgeDays] = useState<string>('');
  const invalidateTasks = useInvalidateTasks();

  const mutation = useMutation({
    mutationFn: async () => {
      const body =
        showMaxAge && maxAgeDays ? { max_age_days: parseInt(maxAgeDays, 10) } : undefined;
      const { data } = await apiClient.post(endpoint, body);
      return data;
    },
    onSuccess: () => {
      toast.success(t('started'));
      invalidateTasks();
    },
    onError: () => {
      toast.error(t('common:error'));
    },
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-base">{t(titleKey)}</CardTitle>
        </div>
        <CardDescription>{t(descriptionKey)}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-3">
          {showMaxAge && (
            <div className="space-y-1">
              <Label htmlFor="max-age">{t('actions.delete-tasks.max-age-label')}</Label>
              <Input
                id="max-age"
                type="number"
                min={1}
                placeholder={t('actions.delete-tasks.max-age-placeholder')}
                value={maxAgeDays}
                onChange={e => setMaxAgeDays(e.target.value)}
                className="w-32"
              />
            </div>
          )}
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending} size="sm">
            {mutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('running')}
              </>
            ) : (
              t('run')
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
