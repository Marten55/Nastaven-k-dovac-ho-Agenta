# Nastavenia najčastejších Elementor widgetov

Hodnoty `settings` sa medzi verziami Elementora líšia. Ak si nie si istý, vlož widget
raz ručne cez UI a prečítaj jeho model:

```js
elementor.getPreviewContainer().children.first().model.get('settings').toJSON()
```

## heading

```js
{ elType: 'widget', widgetType: 'heading', settings: {
  title: 'Text nadpisu',
  header_size: 'h2',
  align: 'center',
  title_color: '#1a1a1a'
}}
```

## text-editor

```js
{ elType: 'widget', widgetType: 'text-editor', settings: {
  editor: '<p>Odstavec textu. HTML je povolené.</p>'
}}
```

## image

```js
{ elType: 'widget', widgetType: 'image', settings: {
  image: { id: 9101, url: 'https://example-shop.sk/wp-content/uploads/foto.jpg' },
  image_size: 'large',
  align: 'center'
}}
```

`id` musí byť skutočné ID prílohy v knižnici médií. Widget so samotnou `url` bez `id`
sa zobrazí, ale Elementor mu nevie generovať responzívne veľkosti.

## button

```js
{ elType: 'widget', widgetType: 'button', settings: {
  text: 'Do košíka',
  link: { url: 'https://example-shop.sk/kosik/', is_external: '', nofollow: '' },
  align: 'center',
  size: 'md'
}}
```

## icon-box

```js
{ elType: 'widget', widgetType: 'icon-box', settings: {
  title_text: 'Doprava zadarmo',
  description_text: 'Pri objednávke nad 100 eur.',
  selected_icon: { value: 'fas fa-truck', library: 'fa-solid' }
}}
```

## kontajner

```js
$e.run('document/elements/create', {
  container: elementor.getPreviewContainer(),
  model: { elType: 'container', settings: {
    flex_direction: 'row',
    content_width: 'boxed'
  }}
});
```

Vrátený objekt má vlastnosť `id`. Ak chceš doň vkladať widgety, použi
`elementor.getContainer(id)` ako `container` pri ďalšom volaní `create`.
