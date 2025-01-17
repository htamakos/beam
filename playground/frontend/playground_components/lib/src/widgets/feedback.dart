/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../playground_components.dart';
import '../assets/assets.gen.dart';

class FeedbackWidget extends StatelessWidget {
  static const positiveRatingButtonKey = Key('positive');
  static const negativeRatingButtonKey = Key('negative');

  final FeedbackController controller;
  final String title;

  const FeedbackWidget({
    required this.controller,
    required this.title,
  });

  void _onRatingChanged(BuildContext context, FeedbackRating rating) {
    controller.rating = rating;

    PlaygroundComponents.analyticsService.sendUnawaited(
      AppRatedAnalyticsEvent(
        rating: rating,
        snippetContext: controller.eventSnippetContext,
        additionalParams: controller.additionalParams,
      ),
    );

    final closeNotifier = PublicNotifier();
    showOverlay(
      context: context,
      closeNotifier: closeNotifier,
      positioned: Positioned(
        bottom: 50,
        left: 20,
        child: OverlayBody(
          child: FeedbackDropdown(
            close: closeNotifier.notifyPublic,
            controller: controller,
            rating: rating,
            title: 'widgets.feedback.title'.tr(),
            subtitle: 'widgets.feedback.hint'.tr(),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, child) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(width: BeamSizes.size6),
          Tooltip(
            message: 'widgets.feedback.positive'.tr(),
            child: InkWell(
              key: positiveRatingButtonKey,
              onTap: () {
                _onRatingChanged(context, FeedbackRating.positive);
              },
              child: _RatingIcon(
                groupValue: controller.rating,
                value: FeedbackRating.positive,
              ),
            ),
          ),
          const SizedBox(width: BeamSizes.size6),
          Tooltip(
            message: 'widgets.feedback.negative'.tr(),
            child: InkWell(
              key: negativeRatingButtonKey,
              onTap: () {
                _onRatingChanged(context, FeedbackRating.negative);
              },
              child: _RatingIcon(
                groupValue: controller.rating,
                value: FeedbackRating.negative,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RatingIcon extends StatelessWidget {
  final FeedbackRating? groupValue;
  final FeedbackRating value;
  const _RatingIcon({
    required this.groupValue,
    required this.value,
  });

  String _getAsset() {
    final isSelected = value == groupValue;
    switch (value) {
      case FeedbackRating.positive:
        return isSelected ? Assets.svg.thumbUpFilled : Assets.svg.thumbUp;
      case FeedbackRating.negative:
        return isSelected ? Assets.svg.thumbDownFilled : Assets.svg.thumbDown;
    }
  }

  @override
  Widget build(BuildContext context) {
    return SvgPicture.asset(
      _getAsset(),
      package: PlaygroundComponents.packageName,
    );
  }
}

class FeedbackDropdown extends StatelessWidget {
  static const sendButtonKey = Key('sendFeedbackButtonKey');
  static const textFieldKey = Key('feedbackTextFieldKey');

  final FeedbackController controller;
  final VoidCallback close;
  final FeedbackRating rating;
  final String title;
  final String subtitle;

  const FeedbackDropdown({
    required this.controller,
    required this.title,
    required this.rating,
    required this.close,
    required this.subtitle,
  });

  void _sendFeedback() {
    PlaygroundComponents.analyticsService.sendUnawaited(
      FeedbackFormSentAnalyticsEvent(
        rating: rating,
        text: controller.textController.text,
        snippetContext: controller.eventSnippetContext,
        additionalParams: controller.additionalParams,
      ),
    );
    controller.textController.clear();
    close();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller.textController,
      builder: (context, child) => Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
        ),
        padding: const EdgeInsets.all(16),
        width: 400,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            const SizedBox(height: BeamSizes.size8),
            Text(
              subtitle,
            ),
            const SizedBox(height: BeamSizes.size8),
            TextField(
              key: textFieldKey,
              controller: controller.textController,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.multiline,
              maxLines: 5,
              minLines: 3,
            ),
            const SizedBox(height: BeamSizes.size8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                ElevatedButton(
                  key: sendButtonKey,
                  onPressed: controller.textController.text.isEmpty
                      ? null
                      : _sendFeedback,
                  child: const Text('widgets.feedback.send').tr(),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
