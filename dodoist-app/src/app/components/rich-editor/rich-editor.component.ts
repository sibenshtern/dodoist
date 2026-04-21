import {
  Component,
  Input,
  Output,
  EventEmitter,
  OnInit,
  OnDestroy,
  OnChanges,
  SimpleChanges,
} from '@angular/core';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { TiptapEditorDirective } from 'ngx-tiptap';

@Component({
  selector: 'app-rich-editor',
  standalone: true,
  imports: [TiptapEditorDirective],
  templateUrl: './rich-editor.component.html',
  styleUrl: './rich-editor.component.scss',
})
export class RichEditorComponent implements OnInit, OnDestroy, OnChanges {
  @Input() value: unknown = null;
  @Input() readonly = false;
  @Input() placeholder = 'Write something…';
  @Output() valueChange = new EventEmitter<unknown>();

  editor!: Editor;

  ngOnInit(): void {
    this.editor = new Editor({
      extensions: [StarterKit],
      editable: !this.readonly,
      content: (this.value as object) ?? '',
      onUpdate: ({ editor }) => {
        this.valueChange.emit(editor.getJSON());
      },
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.editor) return;

    if (changes['readonly']) {
      this.editor.setEditable(!this.readonly);
    }

    if (changes['value'] && !changes['value'].firstChange) {
      const newVal = changes['value'].currentValue;
      const currentJson = JSON.stringify(this.editor.getJSON());
      const newJson = JSON.stringify(newVal ?? '');
      if (currentJson !== newJson) {
        this.editor.commands.setContent((newVal as object) ?? '');
      }
    }
  }

  ngOnDestroy(): void {
    this.editor?.destroy();
  }

  isActive(name: string, attrs?: Record<string, unknown>): boolean {
    return this.editor?.isActive(name, attrs) ?? false;
  }

  get isEmpty(): boolean {
    return this.editor?.isEmpty ?? true;
  }
}
