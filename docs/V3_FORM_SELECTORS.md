# V3 Campaign Creation - Form Selectors

> ⚠️ **TODO:** Come back and fix the V3 from-scratch campaign creation script. Currently having issues with selecting form fields. Need to debug why `force=True` clicks aren't working reliably.

This document contains the HTML selectors for the first-page form fields when creating a campaign from scratch.

URL: `https://advertiser.trafficjunky.com/campaign/drafts/bid/create`

---

## Device (Platform)
**Options:** All | Desktop | Mobile

```html
<input type="radio" name="platform_id" value="1" checked="checked" data-toggle-target="platform_all">
<input type="radio" name="platform_id" value="2" data-toggle-target="platform_desktop">
<input type="radio" name="platform_id" value="3" data-toggle-target="platform_mobile">
```

**Status:** ✅ Fixed

---

## Ad Format Type
**Options:** Display | In-Stream Video | Pop

```html
Display
<input type="radio" name="ad_format_id" value="1" checked="checked" data-toggle-target="ad_format_display">

In-stream Video
<input type="radio" name="ad_format_id" value="2" data-toggle-target="ad_format_video">

Pop if selected has no format type or Ad type
<input type="radio" name="ad_format_id" value="3" data-toggle-target="ad_format_pop">
```

**Status:** ✅ Fixed - `input[name="ad_format_id"][value="1|2|3"]`

---

## Format Type (for Display ads)
**Options:** Banner | Native

```html
Banner:
<span class="btn btn-secondary button active buttonRadiusLeft" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display">Banner<input type="radio" name="format_type_id" value="4" data-toggle-target="format_type_banner" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display"></span>

Native:
<span class="btn btn-secondary button buttonRadiusRight" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display">Native<input type="radio" name="format_type_id" value="5" data-toggle-target="format_type_native" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display"></span>
```

**Status:** ✅ Fixed - `input[name="format_type_id"][value="4|5"]`

---

## Ad Type
**Options:** Static Banner | Video Banner | Rollover

```html
Static banner - Already selected
<span class="btn btn-secondary button active buttonRadiusLeft" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display format_type_banner format_type_native format_type_scrollable">Static Banner<input type="radio" name="ad_type_id" value="1" data-toggle-target="ad_type_static" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display format_type_banner format_type_native format_type_scrollable"></span>

Video Banner: 
<span class="btn btn-secondary button buttonRadiusRight" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display format_type_banner">Video Banner<input type="radio" name="ad_type_id" value="2" data-toggle-target="ad_type_video_banner" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display format_type_banner"></span>

Video File (only for preroll and already selected when In-Stream video selected in Ad format): 
<span class="btn btn-secondary button active buttonRadiusLeft buttonRadiusRight" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_video">Video File<input type="radio" name="ad_type_id" value="5" data-toggle-target="ad_type_video_file" data-enable-on="platform_all platform_desktop platform_mobile ad_format_video"></span>

Rollover (only when Native Format type selected - preselected when choosing Native Format type)
<span class="btn btn-secondary button active buttonRadiusLeft" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display format_type_native">Rollover<input type="radio" name="ad_type_id" value="9" data-toggle-target="ad_type_rollover" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display format_type_native"></span>

Static Banner (only when Native Format type selected)
<span class="btn btn-secondary button buttonRadiusRight" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display format_type_banner format_type_native format_type_scrollable">Static Banner<input type="radio" name="ad_type_id" value="1" data-toggle-target="ad_type_static" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display format_type_banner format_type_native format_type_scrollable"></span>

```

---

## Ad Dimensions
**Options:** 
300x250 | Static Banner / Video Banner (pre-selected)
<span class="btn btn-secondary button active buttonRadiusLeft" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner">300 X 250<input type="radio" name="ad_dimension_id" value="9" data-toggle-target="ad_dimension_9" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner"></span>
950x250 | Static Banner / Video Banner
<span class="btn btn-secondary button" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner">950 X 250<input type="radio" name="ad_dimension_id" value="5" data-toggle-target="ad_dimension_5" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner"></span>
468x60  | Static Banner / Video Banner
<span class="btn btn-secondary button" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner">468 X 60<input type="radio" name="ad_dimension_id" value="25" data-toggle-target="ad_dimension_25" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner"></span>
305x99  | Static Banner / Video Banner
<span class="btn btn-secondary button" data-show-button-on="platform_all platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner">305 X 99<input type="radio" name="ad_dimension_id" value="55" data-toggle-target="ad_dimension_55" data-enable-on="platform_all platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner"></span>
300x100 | Static Banner / Video Banner
<span class="btn btn-secondary button" data-show-button-on="platform_all platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner">300 X 100<input type="radio" name="ad_dimension_id" value="80" data-toggle-target="ad_dimension_80" data-enable-on="platform_all platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner"></span>
970x90  | Static Banner / Video Banner
<span class="btn btn-secondary button" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner">970 X 90<input type="radio" name="ad_dimension_id" value="221" data-toggle-target="ad_dimension_221" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_epom ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner"></span>
320x480 | Static Banner / Video Banner
<span class="btn btn-secondary button buttonRadiusRight" data-show-button-on="platform_all platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner">320 X 480<input type="radio" name="ad_dimension_id" value="9771" data-toggle-target="ad_dimension_9771" data-enable-on="platform_all platform_mobile ad_format_display ad_format_redirect format_type_banner ad_type_iframe ad_type_source_id ad_type_static ad_type_video_banner"></span>
640x360 | Static Banner / Video Banner


640x360 | Native Rollover / Static Banner (only avaialable option for Native Rollover and static banner and already pre-selected)
<span class="btn btn-secondary button active buttonRadiusLeft buttonRadiusRight" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_native ad_type_rollover ad_type_source_id ad_type_static">640 X 360<input type="radio" name="ad_dimension_id" value="9731" data-toggle-target="ad_dimension_9731" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_redirect format_type_native ad_type_rollover ad_type_source_id ad_type_static"></span>

```html
<!-- Paste HTML here -->
```



---

## Content Category
**Options:** Straight | Gay | Trans

```html
Straight (pre Selected)
<span class="btn btn-secondary button active buttonRadiusLeft" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_video ad_format_pop ad_format_tab format_type_banner format_type_scrollable format_type_native ad_type_dynamic_vast ad_type_epom ad_type_iframe ad_type_rollover ad_type_source_id ad_type_static ad_type_static_vast ad_type_video_banner ad_type_video_file ad_dimension_5 ad_dimension_9 ad_dimension_25 ad_dimension_38 ad_dimension_55 ad_dimension_70 ad_dimension_80 ad_dimension_221 ad_dimension_9651 ad_dimension_9731 ad_dimension_9771 ad_dimension_9781">Straight<input type="radio" name="content_category_id" value="straight" data-toggle-target="content_category_straight" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_video ad_format_pop ad_format_tab format_type_banner format_type_scrollable format_type_native ad_type_dynamic_vast ad_type_epom ad_type_iframe ad_type_rollover ad_type_source_id ad_type_static ad_type_static_vast ad_type_video_banner ad_type_video_file ad_dimension_5 ad_dimension_9 ad_dimension_25 ad_dimension_38 ad_dimension_55 ad_dimension_70 ad_dimension_80 ad_dimension_221 ad_dimension_9651 ad_dimension_9731 ad_dimension_9771 ad_dimension_9781"></span>
Gay
<span class="btn btn-secondary button" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_video ad_format_pop format_type_banner format_type_native ad_type_dynamic_vast ad_type_epom ad_type_iframe ad_type_rollover ad_type_source_id ad_type_static ad_type_static_vast ad_type_video_banner ad_type_video_file ad_dimension_5 ad_dimension_9 ad_dimension_25 ad_dimension_38 ad_dimension_55 ad_dimension_80 ad_dimension_221 ad_dimension_9651 ad_dimension_9731 ad_dimension_9771 ad_dimension_9781">Gay<input type="radio" name="content_category_id" value="gay" data-toggle-target="content_category_gay" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_video ad_format_pop format_type_banner format_type_native ad_type_dynamic_vast ad_type_epom ad_type_iframe ad_type_rollover ad_type_source_id ad_type_static ad_type_static_vast ad_type_video_banner ad_type_video_file ad_dimension_5 ad_dimension_9 ad_dimension_25 ad_dimension_38 ad_dimension_55 ad_dimension_80 ad_dimension_221 ad_dimension_9651 ad_dimension_9731 ad_dimension_9771 ad_dimension_9781"></span>
Trans
<span class="btn btn-secondary button buttonRadiusRight" data-show-button-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_video ad_format_pop ad_format_tab format_type_banner format_type_scrollable format_type_native ad_type_dynamic_vast ad_type_epom ad_type_iframe ad_type_rollover ad_type_source_id ad_type_static ad_type_static_vast ad_type_video_banner ad_type_video_file ad_dimension_5 ad_dimension_9 ad_dimension_25 ad_dimension_38 ad_dimension_55 ad_dimension_70 ad_dimension_80 ad_dimension_221 ad_dimension_9651 ad_dimension_9731 ad_dimension_9771 ad_dimension_9781">Trans<input type="radio" name="content_category_id" value="trans" data-toggle-target="content_category_trans" data-enable-on="platform_all platform_desktop platform_mobile ad_format_display ad_format_video ad_format_pop ad_format_tab format_type_banner format_type_scrollable format_type_native ad_type_dynamic_vast ad_type_epom ad_type_iframe ad_type_rollover ad_type_source_id ad_type_static ad_type_static_vast ad_type_video_banner ad_type_video_file ad_dimension_5 ad_dimension_9 ad_dimension_25 ad_dimension_38 ad_dimension_55 ad_dimension_70 ad_dimension_80 ad_dimension_221 ad_dimension_9651 ad_dimension_9731 ad_dimension_9771 ad_dimension_9781"></span>
```

**Status:** ⚠️ Code added but needs testing - `input[name="content_category_id"][value="straight|gay|trans"]`

---

## Labels
**Options:** Multi-select input

```html
<input class="select2-search__field" type="search" tabindex="0" autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false" role="searchbox" aria-autocomplete="list" placeholder="Select or Input a Label">
```

**Status:** ✅ Fixed

---

## Gender (Demographic Targeting)
**Options:** All | Male | Female

```html
All (pre-selected)
<input type="radio" name="demographic_targeting_id" id="demographic_all" value="1" autocomplete="off" checked="" data-listener="true">
Male
<input type="radio" name="demographic_targeting_id" id="demographic_male" value="2" autocomplete="off" data-listener="true">
Female
<input type="radio" name="demographic_targeting_id" id="demographic_female" value="3" autocomplete="off" data-listener="true">
```

**Status:** ✅ Fixed - `input[name="demographic_targeting_id"][value="1|2|3"]`

---

## Notes

- All selectors should use the `name` and `value` attributes for radio buttons
- Example selector: `input[name="platform_id"][value="1"]`
