import { router, Stack, useLocalSearchParams, usePreventRemove } from 'expo-router';
import { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { useToast } from '@/components/Toast';
import { Button, Card, Chip, EmptyState, Field, Loading, Muted, Row, StatTile } from '@/components/ui';
import {
  computeMoney,
  draftStatus,
  editAmount,
  emptyDraft,
  setPaid,
  toUpdateInput,
  cellPaid,
  type Draft,
} from '@/features/chits/gridDraft';
import { useChit, useDeleteChit, useUpdateChit } from '@/features/chits/hooks';
import { MonthView } from '@/features/chits/MonthView';
import { AddMemberSheet, ConfirmSheet, PayoutSheet } from '@/features/chits/Sheets';
import { TableView } from '@/features/chits/TableView';
import { useI18n } from '@/i18n';
import { currentMonthIndex, formatRupees, formatSignedRupees, periodLabel } from '@/lib/format';
import { colors, font, shadow, space } from '@/theme';

export default function ChitScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const chitId = Number(id);
  const toast = useToast();
  const { t, tn, tError } = useI18n();
  const { data: chit, error, isLoading } = useChit(chitId);
  const update = useUpdateChit(chitId);
  const remove = useDeleteChit();

  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [view, setView] = useState<'month' | 'table'>('month');
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null);
  const [payoutMonth, setPayoutMonth] = useState<number | null>(null);
  const [addingMember, setAddingMember] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  // Set when the user tries to leave with unsaved edits; calling it completes the navigation
  const [pendingLeave, setPendingLeave] = useState<(() => void) | null>(null);
  // True once the user chose to leave (or deleted the chit): stop guarding
  const [leaving, setLeaving] = useState(false);

  const money = useMemo(() => (chit ? computeMoney(chit, draft) : null), [chit, draft]);
  const status = chit ? draftStatus(chit, draft) : null;
  const dirty = (status?.dirtyCount ?? 0) > 0;

  // Ask before leaving with unsaved edits (back button, swipe back, header back)
  usePreventRemove(dirty && !leaving, ({ repeat }) => setPendingLeave(() => repeat));

  if (isLoading) return <Loading />;
  if (error || !chit || !money || !status) {
    return (
      <View style={styles.content}>
        <EmptyState
          title={t('grid.couldntOpen')}
          text={tError(error)}
          action={<Button label={t('grid.backToAll')} onPress={() => router.replace('/')} />}
        />
      </View>
    );
  }

  const nowIndex = currentMonthIndex(chit.startMonth);
  const clampedNow = Math.min(Math.max(nowIndex, 1), chit.months);
  const activeMonth = selectedMonth ?? clampedNow;

  async function save() {
    if (!chit || status?.hasErrors) return;
    try {
      await update.mutateAsync(toUpdateInput(chit, draft));
      toast(tn('grid.saved', status!.dirtyCount));
      setDraft(emptyDraft());
    } catch (err) {
      toast(tError(err), 'error');
    }
  }

  async function deleteChit() {
    try {
      await remove.mutateAsync(chitId);
      setLeaving(true);
      toast(t('delete.done', { name: chit!.name }), 'info');
      router.replace('/');
    } catch (err) {
      toast(tError(err), 'error');
      setConfirmDelete(false);
    }
  }

  const togglePaid = (memberId: number, month: number) =>
    setDraft((d) => setPaid(chit, d, [{ memberId, month }], !cellPaid(chit, d, memberId, month)));

  return (
    <View style={{ flex: 1 }}>
      <Stack.Screen options={{ title: chit.name }} />
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Muted>
          {periodLabel(chit.startMonth, chit.months)} ·{' '}
          {t('grid.subtitle', { members: chit.members.length, months: chit.months, amount: formatRupees(chit.perShareAmount) })}
        </Muted>

        <View style={styles.tiles}>
          <StatTile label={t('grid.collected')} value={formatRupees(money.collected)} tone="violet" />
          <StatTile label={t('grid.pendingSoFar')} value={formatRupees(money.pending)} tone="amber" />
          <StatTile label={t('grid.paidOut')} value={formatRupees(money.paidOut)} tone="indigo" />
          <StatTile label={t('grid.profit')} value={formatSignedRupees(money.profit)} tone={money.profit < 0 ? 'rose' : 'emerald'} />
        </View>

        <Card>
          <Row style={{ alignItems: 'flex-start' }}>
            <Field
              style={{ flex: 1 }}
              label={t('grid.chitAmount')}
              value={draft.totalAmount ?? String(chit.totalAmount)}
              onChangeText={(v) => setDraft((d) => ({ ...d, totalAmount: v }))}
              keyboardType="decimal-pad"
              error={status.totalInvalid}
            />
            <Field
              style={{ width: 120 }}
              label={t('grid.commission')}
              hint="%"
              accessibilityLabel={t('grid.commissionAria')}
              value={draft.commission ?? String(chit.commissionPercent)}
              onChangeText={(v) => setDraft((d) => ({ ...d, commission: v }))}
              keyboardType="decimal-pad"
              error={status.commissionInvalid}
            />
          </Row>
        </Card>

        <Row>
          <Chip label={t('grid.monthView')} active={view === 'month'} onPress={() => setView('month')} />
          <Chip label={t('grid.tableView')} active={view === 'table'} onPress={() => setView('table')} />
          <View style={{ flex: 1 }} />
          <Chip label={t('grid.addMember')} onPress={() => setAddingMember(true)} />
        </Row>

        {view === 'month' ? (
          <MonthView
            chit={chit}
            draft={draft}
            money={money}
            month={activeMonth}
            nowIndex={nowIndex}
            onMonthChange={setSelectedMonth}
            onAmountChange={(memberId, month, text) => setDraft((d) => editAmount(chit, d, memberId, month, text))}
            onTogglePaid={togglePaid}
            onToggleMonth={(month, allPaid, ids) =>
              setDraft((d) => setPaid(chit, d, ids.map((memberId) => ({ memberId, month })), !allPaid))
            }
            onOpenPayout={setPayoutMonth}
          />
        ) : (
          <TableView chit={chit} draft={draft} money={money} nowIndex={nowIndex} onTogglePaid={togglePaid} />
        )}

        <Button variant="ghost" label={t('grid.deleteChit')} onPress={() => setConfirmDelete(true)} style={{ marginTop: space.lg }} />
      </ScrollView>

      {dirty ? (
        <View style={styles.saveBar} accessibilityLabel={t('grid.unsavedAria')}>
          <Text style={{ flex: 1, color: colors.text, fontWeight: font.medium }}>
            {tn('grid.unsaved', status.dirtyCount)}
            {status.hasErrors ? t('grid.fixRed') : ''}
          </Text>
          <Button variant="ghost" label={t('grid.discard')} onPress={() => setDraft(emptyDraft())} />
          <Button
            label={update.isPending ? t('common.saving') : t('grid.saveChanges')}
            onPress={save}
            disabled={status.hasErrors}
            busy={update.isPending}
          />
        </View>
      ) : null}

      {/* Mounted only while open, so each opening starts from fresh form state */}
      {payoutMonth !== null ? (
        <PayoutSheet key={payoutMonth} chit={chit} money={money} month={payoutMonth} onClose={() => setPayoutMonth(null)} />
      ) : null}
      {addingMember ? <AddMemberSheet chit={chit} onClose={() => setAddingMember(false)} /> : null}
      <ConfirmSheet
        visible={confirmDelete}
        title={t('delete.title', { name: chit.name })}
        text={t('delete.text')}
        confirmLabel={t('delete.confirm')}
        cancelLabel={t('common.cancel')}
        danger
        busy={remove.isPending}
        onConfirm={deleteChit}
        onClose={() => setConfirmDelete(false)}
      />
      <ConfirmSheet
        visible={pendingLeave !== null}
        title={t('leave.title')}
        text={tn('leave.text', status.dirtyCount)}
        confirmLabel={t('leave.leave')}
        cancelLabel={t('leave.stay')}
        danger
        onConfirm={() => {
          const leave = pendingLeave;
          setLeaving(true);
          setPendingLeave(null);
          leave?.();
        }}
        onClose={() => setPendingLeave(null)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: space.lg, gap: space.lg, paddingBottom: 140 },
  tiles: { flexDirection: 'row', flexWrap: 'wrap', gap: space.md },
  saveBar: {
    position: 'absolute',
    left: space.md,
    right: space.md,
    bottom: space.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: space.md,
    ...shadow,
  },
});
