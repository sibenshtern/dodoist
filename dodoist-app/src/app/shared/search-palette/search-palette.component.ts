import {
  Component, computed, ElementRef, EventEmitter, inject,
  OnDestroy, OnInit, Output, signal, ViewChild,
} from '@angular/core';
import { Router } from '@angular/router';
import { Subject, debounceTime, distinctUntilChanged, switchMap, of, takeUntil } from 'rxjs';
import { SearchService, SearchTask } from '../../services/search.service';

interface GroupedResult {
  projectId: string;
  projectName: string;
  projectColor: string;
  tasks: SearchTask[];
}

const STATUS_LABEL: Record<string, string> = {
  backlog: 'Backlog', todo: 'To Do', in_progress: 'In Progress',
  in_review: 'In Review', done: 'Done', cancelled: 'Cancelled',
};
const PRIORITY_COLOR: Record<string, string> = {
  critical: '#db4035', high: '#ff9800', medium: '#a16207', low: '#299438', none: '#94a3b8',
};
const TYPE_ICON: Record<string, string> = {
  task: '✓', bug: '🐛', story: '📖', epic: '⚡', personal: '◎',
};

@Component({
  selector: 'app-search-palette',
  standalone: true,
  templateUrl: './search-palette.component.html',
  styleUrl: './search-palette.component.scss',
})
export class SearchPaletteComponent implements OnInit, OnDestroy {
  @Output() close = new EventEmitter<void>();
  @ViewChild('searchInput') inputRef!: ElementRef<HTMLInputElement>;

  private readonly searchService = inject(SearchService);
  private readonly router = inject(Router);
  private readonly destroy$ = new Subject<void>();
  private readonly query$ = new Subject<string>();

  readonly query = signal('');
  readonly results = signal<SearchTask[]>([]);
  readonly isLoading = signal(false);
  readonly activeIndex = signal(-1);

  readonly grouped = computed<GroupedResult[]>(() => {
    const map = new Map<string, GroupedResult>();
    for (const t of this.results()) {
      if (!map.has(t.project)) {
        map.set(t.project, {
          projectId: t.project,
          projectName: t.project_name,
          projectColor: t.project_color || '#6b7280',
          tasks: [],
        });
      }
      map.get(t.project)!.tasks.push(t);
    }
    return [...map.values()];
  });

  readonly flatResults = computed(() => this.results());

  ngOnInit(): void {
    this.query$.pipe(
      debounceTime(280),
      distinctUntilChanged(),
      switchMap(q => {
        if (q.trim().length < 2) { this.results.set([]); this.isLoading.set(false); return of([]); }
        this.isLoading.set(true);
        return this.searchService.search(q.trim());
      }),
      takeUntil(this.destroy$),
    ).subscribe({
      next: res => { this.results.set(res); this.isLoading.set(false); this.activeIndex.set(res.length > 0 ? 0 : -1); },
      error: () => { this.isLoading.set(false); },
    });

    setTimeout(() => this.inputRef?.nativeElement.focus(), 30);
  }

  ngOnDestroy(): void { this.destroy$.next(); this.destroy$.complete(); }

  onInput(event: Event): void {
    const q = (event.target as HTMLInputElement).value;
    this.query.set(q);
    this.isLoading.set(q.trim().length >= 2);
    this.query$.next(q);
  }

  onKeydown(event: KeyboardEvent): void {
    const len = this.flatResults().length;
    if (len === 0) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.activeIndex.update(i => Math.min(i + 1, len - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.activeIndex.update(i => Math.max(i - 1, 0));
    } else if (event.key === 'Enter') {
      const task = this.flatResults()[this.activeIndex()];
      if (task) this.openTask(task);
    }
  }

  openTask(task: SearchTask): void {
    this.router.navigate(['/task', task.id]);
    this.close.emit();
  }

  statusLabel(s: string): string { return STATUS_LABEL[s] ?? s; }
  priorityColor(p: string): string { return PRIORITY_COLOR[p] ?? '#94a3b8'; }
  typeIcon(t: string): string { return TYPE_ICON[t] ?? '✓'; }

  isActive(task: SearchTask): boolean {
    return this.flatResults().indexOf(task) === this.activeIndex();
  }

  setActive(task: SearchTask): void {
    this.activeIndex.set(this.flatResults().indexOf(task));
  }
}
