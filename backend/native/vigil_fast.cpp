// C++ version of the per-signal tracker in backend/app/engine/drift.py.
// Results must match the Python version exactly. tests/test_native.py checks this.
// Build with: make native

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

namespace {

const double MAD_TO_SD = 1.4826;
const uint8_t FIRED_Z = 1, FIRED_EWMA = 2, FIRED_CUSUM = 4;
enum Method : int32_t { METHOD_Z = 0, METHOD_EWMA = 1, METHOD_CUSUM = 2, METHOD_VOTE = 3 };

double median(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    const size_t n = values.size();
    return n % 2 == 1 ? values[n / 2] : (values[n / 2 - 1] + values[n / 2]) / 2;
}

std::vector<double> last(const std::vector<double>& values, int32_t count) {
    const size_t keep = std::min(values.size(), static_cast<size_t>(count));
    return std::vector<double>(values.end() - keep, values.end());
}

}  // namespace

extern "C" {

struct VigilParams {
    int32_t short_window, reference_window, needed, persist, release, max_freeze, method, votes_needed;
    double sigma_floor, sign, z_limit, ewma_lambda, cusum_k, cusum_h, limit, dead_zone, evidence_cap;
};

int vigil_track(const double* values, int32_t n, const VigilParams* p, double* last_value, double* out_median, double* out_sigma,
                double* out_short, double* out_ewma, double* out_evidence, uint8_t* out_learning, uint8_t* out_flagged,
                uint8_t* out_fired, int32_t* out_drift_days) {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    std::vector<double> history;
    double ewma = 0, cusum = 0, latest = nan;
    int32_t flag_start = 0, true_run = 0, false_run = 0;  // flag_start 0 means no flag: days start at 1
    uint8_t fired = 0;

    for (int32_t i = 0; i < n; i++) {
        const int32_t day = i + 1;
        const double value = values[i];
        double med = nan, sigma = nan, recent = nan;
        bool learning = true;
        if (!history.empty()) {
            const std::vector<double> window = last(history, p->reference_window);
            med = median(window);
            std::vector<double> deviations;
            deviations.reserve(window.size());
            for (double v : window) deviations.push_back(std::fabs(v - med));
            sigma = std::max(MAD_TO_SD * median(deviations), p->sigma_floor);
            recent = median(last(history, p->short_window));
            learning = static_cast<int32_t>(history.size()) < p->needed;
        }
        if (!std::isnan(value)) {
            latest = value;
            if (!learning) {
                const double r = p->sign * (value - med) / sigma;
                ewma = p->ewma_lambda * r + (1 - p->ewma_lambda) * ewma;
                cusum = std::max(0.0, cusum + r - p->cusum_k);
                fired = static_cast<uint8_t>((r >= p->z_limit ? FIRED_Z : 0) | (ewma >= p->limit ? FIRED_EWMA : 0) |
                                             (cusum >= p->cusum_h ? FIRED_CUSUM : 0));
                bool active;
                if (p->method == METHOD_VOTE) {
                    active = ((fired & FIRED_Z) != 0) + ((fired & FIRED_EWMA) != 0) + ((fired & FIRED_CUSUM) != 0) >= p->votes_needed;
                } else {
                    active = (fired & (p->method == METHOD_Z ? FIRED_Z : p->method == METHOD_EWMA ? FIRED_EWMA : FIRED_CUSUM)) != 0;
                }
                true_run = active ? true_run + 1 : 0;
                false_run = active ? 0 : false_run + 1;
                if (flag_start == 0 && true_run >= p->persist) {
                    flag_start = day - true_run + 1;
                } else if (flag_start != 0 && false_run >= p->release) {
                    flag_start = 0;
                }
            }
            // A flagged reading stays out of the baseline until the change is accepted as the new normal.
            if (flag_start == 0 || day - flag_start > p->max_freeze) history.push_back(value);
        }
        const bool flagged = flag_start != 0;
        const double raw = (ewma / p->limit - p->dead_zone) / (1 - p->dead_zone);
        last_value[i] = latest;
        out_median[i] = med;
        out_sigma[i] = sigma;
        out_short[i] = recent;
        out_ewma[i] = ewma;
        out_evidence[i] = std::min(std::max(std::max(raw, flagged ? 1.0 : 0.0), 0.0), p->evidence_cap);
        out_learning[i] = learning;
        out_flagged[i] = flagged;
        out_fired[i] = fired;
        out_drift_days[i] = flagged ? day - flag_start + 1 : 0;
    }
    return 0;
}

}  // extern "C"
