package com.agrovision.app.core.ml

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.ln
import kotlin.random.Random

/**
 * Qurilma ichida o'qitiladigan haqiqiy ansambl modellari — desktop
 * versiyadagi scikit-learn `RandomForestRegressor`, `RandomForestClassifier`
 * va `GradientBoostingClassifier` ning sof-Kotlin ekvivalentlari.
 *
 * Bu "soddalashtirilgan chiziqli approksimatsiya" emas: CART daraxtlari
 * dispersiya/Gini kamayishi bo'yicha haqiqiy bo'linish qidiradi, bagging va
 * xususiyat-subsampling qo'llanadi, gradient boosting Nyuton qadamli
 * logistik yo'qotish bilan ishlaydi. Modellar JSON sifatida bazaga saqlanadi.
 */

// ---------------------------------------------------------------------------
// Daraxt tuzilmasi
// ---------------------------------------------------------------------------
sealed class TreeNode {
    data class Leaf(val values: DoubleArray) : TreeNode()
    data class Split(
        val feature: Int,
        val threshold: Double,
        val left: TreeNode,
        val right: TreeNode,
    ) : TreeNode()

    fun predict(x: DoubleArray): DoubleArray = when (this) {
        is Leaf -> values
        is Split -> if (x[feature] <= threshold) left.predict(x) else right.predict(x)
    }

    fun toJson(): JSONObject = when (this) {
        is Leaf -> JSONObject().put("v", JSONArray().also { arr -> values.forEach { arr.put(it) } })
        is Split -> JSONObject()
            .put("f", feature).put("t", threshold)
            .put("l", left.toJson()).put("r", right.toJson())
    }

    companion object {
        fun fromJson(json: JSONObject): TreeNode =
            if (json.has("v")) {
                val arr = json.getJSONArray("v")
                Leaf(DoubleArray(arr.length()) { arr.getDouble(it) })
            } else {
                Split(
                    json.getInt("f"), json.getDouble("t"),
                    fromJson(json.getJSONObject("l")), fromJson(json.getJSONObject("r")),
                )
            }
    }
}

/** Daraxt o'qitish parametrlari. */
data class TreeParams(
    val maxDepth: Int = 12,
    val minSamplesLeaf: Int = 2,
    val minSamplesSplit: Int = 4,
    /** Har bo'linishda ko'riladigan xususiyatlar soni (null → barchasi). */
    val maxFeatures: Int? = null,
    /** Har xususiyat uchun sinaladigan chegara nomzodlari soni. */
    val maxThresholds: Int = 12,
)

/**
 * CART daraxt quruvchi. `criterion` regressiya (dispersiya) yoki
 * klassifikatsiya (Gini) rejimida ishlaydi — ikkalasi ham bir xil
 * "leaf = vektor" ko'rinishida qaytaradi (regressiyada 1 element,
 * klassifikatsiyada sinf ehtimolliklari).
 */
class CartBuilder(
    private val x: Array<DoubleArray>,
    /** Regressiya: y[i] = [target]; Klassifikatsiya: y[i] = one-hot vektor. */
    private val y: Array<DoubleArray>,
    private val params: TreeParams,
    private val random: Random,
    private val classification: Boolean,
) {
    private val featureCount = if (x.isEmpty()) 0 else x[0].size
    private val outputSize = if (y.isEmpty()) 1 else y[0].size

    fun build(indices: IntArray): TreeNode = grow(indices, 0)

    private fun grow(indices: IntArray, depth: Int): TreeNode {
        if (indices.size < params.minSamplesSplit || depth >= params.maxDepth) return leafOf(indices)
        val impurityBefore = impurity(indices)
        if (impurityBefore <= 1e-12) return leafOf(indices)

        var bestGain = 0.0
        var bestFeature = -1
        var bestThreshold = 0.0
        var bestLeft: IntArray? = null
        var bestRight: IntArray? = null

        for (feature in sampledFeatures()) {
            for (threshold in candidateThresholds(indices, feature)) {
                val left = indices.filter { x[it][feature] <= threshold }.toIntArray()
                if (left.size < params.minSamplesLeaf) continue
                val right = indices.filter { x[it][feature] > threshold }.toIntArray()
                if (right.size < params.minSamplesLeaf) continue
                val weighted = (left.size * impurity(left) + right.size * impurity(right)) / indices.size
                val gain = impurityBefore - weighted
                if (gain > bestGain) {
                    bestGain = gain
                    bestFeature = feature
                    bestThreshold = threshold
                    bestLeft = left
                    bestRight = right
                }
            }
        }

        if (bestFeature < 0 || bestLeft == null || bestRight == null || bestGain <= 1e-12) {
            return leafOf(indices)
        }
        return TreeNode.Split(
            bestFeature, bestThreshold,
            grow(bestLeft, depth + 1), grow(bestRight, depth + 1),
        )
    }

    private fun sampledFeatures(): List<Int> {
        val m = params.maxFeatures ?: featureCount
        if (m >= featureCount) return (0 until featureCount).toList()
        return (0 until featureCount).shuffled(random).take(m)
    }

    /** Kvantil asosidagi chegara nomzodlari — barcha nuqtalarni sinashdan tez. */
    private fun candidateThresholds(indices: IntArray, feature: Int): List<Double> {
        val values = indices.map { x[it][feature] }.distinct().sorted()
        if (values.size < 2) return emptyList()
        if (values.size <= params.maxThresholds + 1) {
            return (0 until values.size - 1).map { (values[it] + values[it + 1]) / 2.0 }
        }
        return (1..params.maxThresholds).map { q ->
            val position = (values.size - 1) * q.toDouble() / (params.maxThresholds + 1)
            val low = position.toInt().coerceIn(0, values.size - 2)
            (values[low] + values[low + 1]) / 2.0
        }.distinct()
    }

    private fun impurity(indices: IntArray): Double = if (classification) gini(indices) else variance(indices)

    private fun variance(indices: IntArray): Double {
        if (indices.isEmpty()) return 0.0
        var sum = 0.0
        for (i in indices) sum += y[i][0]
        val mean = sum / indices.size
        var acc = 0.0
        for (i in indices) {
            val diff = y[i][0] - mean
            acc += diff * diff
        }
        return acc / indices.size
    }

    private fun gini(indices: IntArray): Double {
        if (indices.isEmpty()) return 0.0
        val counts = DoubleArray(outputSize)
        for (i in indices) for (c in 0 until outputSize) counts[c] += y[i][c]
        val total = counts.sum().let { if (it <= 0) 1.0 else it }
        var sum = 0.0
        for (c in 0 until outputSize) {
            val p = counts[c] / total
            sum += p * p
        }
        return 1.0 - sum
    }

    private fun leafOf(indices: IntArray): TreeNode.Leaf {
        val values = DoubleArray(outputSize)
        if (indices.isEmpty()) return TreeNode.Leaf(values)
        for (i in indices) for (c in 0 until outputSize) values[c] += y[i][c]
        for (c in 0 until outputSize) values[c] /= indices.size
        return TreeNode.Leaf(values)
    }
}

// ---------------------------------------------------------------------------
// Random Forest — regressiya
// ---------------------------------------------------------------------------
class RandomForestRegressor(val trees: List<TreeNode>) {

    fun predict(features: DoubleArray): Double =
        if (trees.isEmpty()) 0.0 else trees.sumOf { it.predict(features)[0] } / trees.size

    fun toJson(): String = JSONObject()
        .put("type", "rf_regressor")
        .put("trees", JSONArray().also { arr -> trees.forEach { arr.put(it.toJson()) } })
        .toString()

    companion object {
        fun train(
            x: Array<DoubleArray>,
            y: DoubleArray,
            nEstimators: Int = 80,
            seed: Long = 42,
            params: TreeParams = TreeParams(maxFeatures = maxOf(1, (x.firstOrNull()?.size ?: 1) * 2 / 3)),
        ): RandomForestRegressor {
            if (x.isEmpty()) return RandomForestRegressor(emptyList())
            val targets = Array(y.size) { doubleArrayOf(y[it]) }
            val random = Random(seed)
            val trees = (0 until nEstimators).map { t ->
                val treeRandom = Random(seed + t * 7919L)
                val bootstrap = IntArray(x.size) { random.nextInt(x.size) }
                CartBuilder(x, targets, params, treeRandom, classification = false).build(bootstrap)
            }
            return RandomForestRegressor(trees)
        }

        fun fromJson(payload: String): RandomForestRegressor {
            val arr = JSONObject(payload).getJSONArray("trees")
            return RandomForestRegressor((0 until arr.length()).map { TreeNode.fromJson(arr.getJSONObject(it)) })
        }
    }
}

// ---------------------------------------------------------------------------
// Random Forest — ko'p sinfli klassifikatsiya (ekin tavsiyasi)
// ---------------------------------------------------------------------------
class RandomForestClassifier(val trees: List<TreeNode>, val classes: List<Long>) {

    fun predictProba(features: DoubleArray): DoubleArray {
        val result = DoubleArray(classes.size)
        if (trees.isEmpty()) return result
        for (tree in trees) {
            val leaf = tree.predict(features)
            for (c in classes.indices) result[c] += leaf.getOrElse(c) { 0.0 }
        }
        val total = result.sum().let { if (it <= 0) 1.0 else it }
        for (c in result.indices) result[c] /= total
        return result
    }

    fun accuracy(x: Array<DoubleArray>, labels: List<Long>): Double {
        if (x.isEmpty()) return 0.0
        var correct = 0
        for (i in x.indices) {
            val proba = predictProba(x[i])
            val predicted = classes[proba.indices.maxByOrNull { proba[it] } ?: 0]
            if (predicted == labels[i]) correct++
        }
        return correct.toDouble() / x.size
    }

    fun toJson(): String = JSONObject()
        .put("type", "rf_classifier")
        .put("classes", JSONArray().also { arr -> classes.forEach { arr.put(it) } })
        .put("trees", JSONArray().also { arr -> trees.forEach { arr.put(it.toJson()) } })
        .toString()

    companion object {
        fun train(
            x: Array<DoubleArray>,
            labels: List<Long>,
            nEstimators: Int = 60,
            seed: Long = 42,
            params: TreeParams = TreeParams(maxDepth = 10, maxFeatures = maxOf(1, (x.firstOrNull()?.size ?: 1) * 2 / 3)),
        ): RandomForestClassifier {
            if (x.isEmpty()) return RandomForestClassifier(emptyList(), emptyList())
            val classes = labels.distinct().sorted()
            val index = classes.withIndex().associate { (i, c) -> c to i }
            val oneHot = Array(labels.size) { i ->
                DoubleArray(classes.size).also { it[index.getValue(labels[i])] = 1.0 }
            }
            val random = Random(seed)
            val trees = (0 until nEstimators).map { t ->
                val treeRandom = Random(seed + t * 6247L)
                val bootstrap = IntArray(x.size) { random.nextInt(x.size) }
                CartBuilder(x, oneHot, params, treeRandom, classification = true).build(bootstrap)
            }
            return RandomForestClassifier(trees, classes)
        }

        fun fromJson(payload: String): RandomForestClassifier {
            val json = JSONObject(payload)
            val classesArr = json.getJSONArray("classes")
            val classes = (0 until classesArr.length()).map { classesArr.getLong(it) }
            val treesArr = json.getJSONArray("trees")
            val trees = (0 until treesArr.length()).map { TreeNode.fromJson(treesArr.getJSONObject(it)) }
            return RandomForestClassifier(trees, classes)
        }
    }
}

// ---------------------------------------------------------------------------
// Gradient Boosting — binar klassifikatsiya (kasallik xavfi)
// ---------------------------------------------------------------------------
class GradientBoostingClassifier(
    val initLogOdds: Double,
    val learningRate: Double,
    val trees: List<TreeNode>,
) {
    /** Musbat sinf ehtimolligi. */
    fun predictProba(features: DoubleArray): Double {
        var f = initLogOdds
        for (tree in trees) f += learningRate * tree.predict(features)[0]
        return 1.0 / (1.0 + exp(-f))
    }

    fun accuracy(x: Array<DoubleArray>, y: IntArray): Double {
        if (x.isEmpty()) return 0.0
        var correct = 0
        for (i in x.indices) {
            val predicted = if (predictProba(x[i]) >= 0.5) 1 else 0
            if (predicted == y[i]) correct++
        }
        return correct.toDouble() / x.size
    }

    fun toJson(): String = JSONObject()
        .put("type", "gb_classifier")
        .put("init", initLogOdds)
        .put("lr", learningRate)
        .put("trees", JSONArray().also { arr -> trees.forEach { arr.put(it.toJson()) } })
        .toString()

    companion object {
        fun train(
            x: Array<DoubleArray>,
            y: IntArray,
            nEstimators: Int = 60,
            learningRate: Double = 0.1,
            seed: Long = 42,
            params: TreeParams = TreeParams(maxDepth = 3, minSamplesLeaf = 5),
        ): GradientBoostingClassifier {
            if (x.isEmpty()) return GradientBoostingClassifier(0.0, learningRate, emptyList())
            val positives = y.count { it == 1 }.toDouble()
            val rate = (positives / y.size).coerceIn(1e-6, 1 - 1e-6)
            val init = ln(rate / (1 - rate))

            val f = DoubleArray(x.size) { init }
            val trees = ArrayList<TreeNode>(nEstimators)
            val allIndices = IntArray(x.size) { it }

            repeat(nEstimators) { round ->
                // Logistik yo'qotish gradienti (psevdo-qoldiqlar) va Nyuton vazni
                val residual = Array(x.size) { i ->
                    val p = 1.0 / (1.0 + exp(-f[i]))
                    doubleArrayOf(y[i] - p)
                }
                val tree = CartBuilder(
                    x, residual, params, Random(seed + round * 5381L), classification = false,
                ).build(allIndices)
                // Nyuton qadam bilan barglarni kalibrlash: γ = Σr / Σp(1−p)
                val calibrated = calibrate(tree, x, f, allIndices)
                for (i in x.indices) f[i] += learningRate * calibrated.predict(x[i])[0]
                trees += calibrated
            }
            return GradientBoostingClassifier(init, learningRate, trees)
        }

        /**
         * Bargdagi o'rtacha qoldiqni Nyuton qadamiga almashtiradi — bu
         * scikit-learn `GradientBoostingClassifier` ning `LogOddsEstimator`
         * yondashuvi bilan bir xil va konvergensiyani sezilarli tezlashtiradi.
         */
        private fun calibrate(
            node: TreeNode,
            x: Array<DoubleArray>,
            f: DoubleArray,
            indices: IntArray,
        ): TreeNode = when (node) {
            is TreeNode.Leaf -> {
                var numerator = 0.0
                var denominator = 0.0
                for (i in indices) {
                    val p = 1.0 / (1.0 + exp(-f[i]))
                    numerator += node.values[0]
                    denominator += p * (1 - p)
                }
                val gamma = if (abs(denominator) < 1e-9) 0.0 else numerator / denominator
                TreeNode.Leaf(doubleArrayOf(gamma.coerceIn(-8.0, 8.0)))
            }
            is TreeNode.Split -> {
                val left = indices.filter { x[it][node.feature] <= node.threshold }.toIntArray()
                val right = indices.filter { x[it][node.feature] > node.threshold }.toIntArray()
                TreeNode.Split(
                    node.feature, node.threshold,
                    calibrate(node.left, x, f, if (left.isEmpty()) indices else left),
                    calibrate(node.right, x, f, if (right.isEmpty()) indices else right),
                )
            }
        }

        fun fromJson(payload: String): GradientBoostingClassifier {
            val json = JSONObject(payload)
            val arr = json.getJSONArray("trees")
            return GradientBoostingClassifier(
                json.getDouble("init"), json.getDouble("lr"),
                (0 until arr.length()).map { TreeNode.fromJson(arr.getJSONObject(it)) },
            )
        }
    }
}

/** Model sifatini baholash yordamchilari. */
object Metrics {
    fun r2(actual: DoubleArray, predicted: DoubleArray): Double {
        if (actual.isEmpty()) return 0.0
        val mean = actual.average()
        var ssRes = 0.0
        var ssTot = 0.0
        for (i in actual.indices) {
            ssRes += (actual[i] - predicted[i]) * (actual[i] - predicted[i])
            ssTot += (actual[i] - mean) * (actual[i] - mean)
        }
        return if (ssTot < 1e-9) 1.0 else 1.0 - ssRes / ssTot
    }

    /** Train/test bo'linishi (desktop `train_test_split(test_size=0.2, random_state=42)`). */
    fun trainTestSplit(size: Int, testRatio: Double = 0.2, seed: Long = 42): Pair<IntArray, IntArray> {
        val shuffled = (0 until size).shuffled(Random(seed))
        val testSize = (size * testRatio).toInt().coerceAtLeast(1).coerceAtMost(size - 1)
        return shuffled.drop(testSize).toIntArray() to shuffled.take(testSize).toIntArray()
    }
}
